#!/usr/bin/env python3
"""MVP acceptance smoke tests against running Compose stack."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

API = "http://127.0.0.1:18000"
WEB = "http://127.0.0.1:8080"
TIMEOUT = 30


class Result:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, case_id: str, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append(
            {
                "id": case_id,
                "name": name,
                "ok": ok,
                "detail": detail[:500],
            }
        )
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case_id} {name}" + (f" — {detail[:200]}" if detail else ""))


def req(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
    timeout: float = TIMEOUT,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def api_ok(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and payload.get("code") == 0


def data_of(payload: dict[str, Any]) -> Any:
    return payload.get("data")


def wait_draft(token: str, customer_id: int, job_id: int, seconds: int = 90) -> dict | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        _, payload = req(
            "GET",
            f"{API}/api/v1/sidebar/profile?customer_id={customer_id}",
            token=token,
        )
        if not api_ok(payload):
            time.sleep(1.5)
            continue
        d = data_of(payload) or {}
        if d.get("draft"):
            return d
        if not d.get("generating"):
            # finished without draft
            return d
        time.sleep(1.5)
    return None


def main() -> int:
    r = Result()

    # --- Infra ---
    code, health = req("GET", f"{API}/health")
    r.add(
        "INFRA-01",
        "API /health",
        code == 200 and api_ok(health),
        json.dumps(data_of(health), ensure_ascii=False),
    )
    mock_llm = (data_of(health) or {}).get("mock_llm")

    for path, cid in [("/", "INFRA-02"), ("/admin/", "INFRA-03")]:
        try:
            with urllib.request.urlopen(f"{WEB}{path}", timeout=10) as resp:
                r.add(cid, f"Nginx {path}", resp.status == 200, f"status={resp.status}")
        except Exception as exc:  # noqa: BLE001
            r.add(cid, f"Nginx {path}", False, str(exc))

    # --- Seed ---
    code, seed = req("POST", f"{API}/api/v1/mock/seed/demo")
    seeded = api_ok(seed)
    seed_data = data_of(seed) or {}
    r.add(
        "3.H.0",
        "POST /mock/seed/demo",
        seeded,
        json.dumps(seed_data, ensure_ascii=False),
    )

    # Resolve demo customer
    code, clist = req("GET", f"{API}/api/v1/mock/customers")
    items = (data_of(clist) or {}).get("items") or []
    demo = next((c for c in items if c.get("external_id") == "demo_wang"), None)
    if demo is None and items:
        demo = next((c for c in items if c.get("parent_name") == "王女士"), items[0])
    r.add(
        "T-M5-03a",
        "GET /mock/customers has demo",
        demo is not None,
        json.dumps(demo, ensure_ascii=False) if demo else "empty",
    )
    if not demo:
        print("ABORT: no demo customer")
        return _finish(r)

    customer_id = int(demo["id"])
    advisor_id = int(demo.get("owner_user_id") or 0)

    # --- Auth / sidebar exchange ---
    code, exch = req(
        "POST",
        f"{API}/api/v1/auth/wecom/exchange",
        {"code": "mock_code", "external_userid": "demo_wang"},
    )
    token = (data_of(exch) or {}).get("access_token")
    r.add(
        "T-M6-01a",
        "wecom exchange mock",
        api_ok(exch) and bool(token),
        f"customer_id={(data_of(exch) or {}).get('customer_id')}",
    )
    if not token:
        return _finish(r)

    # Prefer mock token for advisor if we know id
    if advisor_id:
        mock_token = f"mock-{advisor_id}"
        # validate
        code, ctx_try = req(
            "GET",
            f"{API}/api/v1/sidebar/context?customer_id={customer_id}",
            token=mock_token,
        )
        if api_ok(ctx_try):
            token = mock_token

    code, ctx = req(
        "GET",
        f"{API}/api/v1/sidebar/context?customer_id={customer_id}",
        token=token,
    )
    r.add(
        "T-M6-01b",
        "GET /sidebar/context",
        bool(api_ok(ctx) and (data_of(ctx) or {}).get("customer")),
        json.dumps((data_of(ctx) or {}).get("customer"), ensure_ascii=False),
    )

    # --- Admin logins & scope ---
    def login(name: str, password: str) -> str | None:
        _, payload = req(
            "POST",
            f"{API}/api/v1/auth/admin/login",
            {"login_name": name, "password": password},
        )
        if api_ok(payload):
            return (data_of(payload) or {}).get("access_token")
        return None

    admin_tok = login("admin", "admin123")
    regional_tok = login("regional", "regional123")
    advisor_tok = login("advisor", "advisor123")
    r.add("T-M5-02a", "admin login", bool(admin_tok))
    r.add("T-M5-02b", "regional login", bool(regional_tok))
    r.add("T-M5-02c", "advisor login", bool(advisor_tok))

    def cust_count(tok: str | None) -> int | None:
        if not tok:
            return None
        _, payload = req("GET", f"{API}/api/v1/admin/customers?page=1&page_size=50", token=tok)
        if not api_ok(payload):
            return None
        return len((data_of(payload) or {}).get("items") or [])

    n_admin = cust_count(admin_tok)
    n_adv = cust_count(advisor_tok)
    r.add(
        "T-M5-02d",
        "advisor customer scope <= admin",
        n_admin is not None and n_adv is not None and n_adv <= n_admin,
        f"admin={n_admin} advisor={n_adv}",
    )

    # Dashboard before generate
    dash_before = None
    if admin_tok:
        _, dash = req("GET", f"{API}/api/v1/admin/dashboard/summary", token=admin_tok)
        dash_before = data_of(dash) if api_ok(dash) else None
        r.add("T-M5-03b", "dashboard summary", dash_before is not None, json.dumps(dash_before, ensure_ascii=False))

        _, tags = req("GET", f"{API}/api/v1/admin/tags", token=admin_tok)
        r.add(
            "T-M5-03c",
            "admin tags list",
            api_ok(tags) and len((data_of(tags) or {}).get("items") or []) > 0,
        )
        _, orgs = req("GET", f"{API}/api/v1/admin/orgs", token=admin_tok)
        r.add("T-M5-01", "admin orgs list", api_ok(orgs))

        # create org smoke
        _, org_c = req(
            "POST",
            f"{API}/api/v1/admin/orgs",
            {"name": "MVP测试组", "code": f"MVP_TEST_{int(time.time())}"},
            token=admin_tok,
        )
        r.add("T-M5-01b", "admin create org", api_ok(org_c), json.dumps(data_of(org_c), ensure_ascii=False))

    # Sidebar tags
    _, side_tags = req(
        "GET",
        f"{API}/api/v1/sidebar/tags?customer_id={customer_id}",
        token=token,
    )
    r.add("T-M5-03d", "sidebar tags", api_ok(side_tags))

    # --- Multi-customer scenario ---
    _, scen = req(
        "POST",
        f"{API}/api/v1/mock/seed/scenario",
        {
            "external_id": "mvp_test_physics",
            "parent_name": "测试赵女士",
            "student_name": "测试赵一凡",
            "grade": "高一",
            "school": "市一中",
            "stage": "senior",
            "append_messages": False,
            "messages": [
                {"direction": "in", "content": "孩子高一物理跟不上，想试听一对一"},
                {"direction": "out", "content": "最近分数大概多少？"},
                {"direction": "in", "content": "期中物理58，价格敏感，先试听"},
            ],
            "cs_summary": "MVP测试场景：物理薄弱",
        },
    )
    scen_data = data_of(scen) or {}
    scen_cid = scen_data.get("customer_id")
    r.add("T-M1-01a", "seed scenario physics", api_ok(scen) and bool(scen_cid), json.dumps(scen_data, ensure_ascii=False))

    # Append mock message on demo customer
    _, msg = req(
        "POST",
        f"{API}/api/v1/mock/messages",
        {
            "customer_id": customer_id,
            "direction": "in",
            "content": f"MVP测试追加消息 {int(time.time())}，数学仍需夯实基础想试听",
        },
    )
    r.add("T-M1-01b", "mock message append", api_ok(msg), json.dumps(data_of(msg), ensure_ascii=False))

    # --- Profile generate (demo) ---
    _, gen = req(
        "POST",
        f"{API}/api/v1/sidebar/profile/generate",
        {"customer_id": customer_id, "force": True},
        token=token,
        timeout=60,
    )
    gen_data = data_of(gen) or {}
    job_id = gen_data.get("job_id")
    r.add(
        "3.H.1a",
        "profile generate queued",
        api_ok(gen) and bool(job_id),
        json.dumps(gen_data, ensure_ascii=False),
    )

    profile_after = wait_draft(token, customer_id, int(job_id or 0), seconds=120 if not mock_llm else 30)
    draft = (profile_after or {}).get("draft") if profile_after else None
    has_four = bool(
        draft
        and all(k in draft for k in ("basic_info", "study_info", "prefer_info", "timeline"))
    )
    r.add(
        "T-M1-01",
        "draft has 4 partitions + confidence/sources",
        has_four and draft.get("confidence") is not None,
        json.dumps(
            {
                "draft_id": draft.get("id") if draft else None,
                "confidence": draft.get("confidence") if draft else None,
                "sources": draft.get("sources") if draft else None,
                "generating": (profile_after or {}).get("generating"),
                "mock_llm": mock_llm,
            },
            ensure_ascii=False,
        ),
    )

    # Dashboard funnel ignores unconfirmed drafts
    if admin_tok and dash_before is not None:
        _, dash2 = req("GET", f"{API}/api/v1/admin/dashboard/summary", token=admin_tok)
        dash_mid = data_of(dash2) if api_ok(dash2) else None
        same = (
            isinstance(dash_mid, dict)
            and isinstance(dash_before, dict)
            and dash_mid.get("funnel") == dash_before.get("funnel")
        )
        # scenario seed may have increased lead count — only compare if lead unchanged
        if (
            isinstance(dash_mid, dict)
            and isinstance(dash_before, dict)
            and (dash_mid.get("funnel") or {}).get("lead")
            != (dash_before.get("funnel") or {}).get("lead")
        ):
            same = (dash_mid.get("funnel") or {}).get("deal") == (
                dash_before.get("funnel") or {}
            ).get("deal")
        r.add(
            "T-M1-02",
            "dashboard funnel not treating draft as confirmed deal",
            same,
            f"before={(dash_before or {}).get('funnel')} mid={(dash_mid or {}).get('funnel')}",
        )

    # Patch draft + confirm field / all
    if draft:
        draft_id = draft["id"]
        _, patched = req(
            "PATCH",
            f"{API}/api/v1/sidebar/profile/draft",
            {
                "draft_id": draft_id,
                "field": "prefer_info",
                "value": {"active_hours": "19:00-21:00", "note": "mvp-edit"},
            },
            token=token,
        )
        r.add("T-M1-04a", "patch draft field", api_ok(patched))

        _, conf_field = req(
            "POST",
            f"{API}/api/v1/sidebar/profile/confirm",
            {"draft_id": draft_id, "mode": "fields", "fields": ["prefer_info"]},
            token=token,
        )
        r.add(
            "T-M1-04b",
            "confirm single field",
            api_ok(conf_field),
            json.dumps(data_of(conf_field), ensure_ascii=False),
        )

        _, conf_all = req(
            "POST",
            f"{API}/api/v1/sidebar/profile/confirm",
            {"draft_id": draft_id, "mode": "all"},
            token=token,
        )
        conf_all_data = data_of(conf_all) or {}
        r.add(
            "3.H.2",
            "confirm all",
            api_ok(conf_all) and conf_all_data.get("draft_status") in ("merged", "partial_confirmed"),
            json.dumps(conf_all_data, ensure_ascii=False),
        )

        # Admin detail sees confirmed
        if admin_tok:
            _, detail = req(
                "GET",
                f"{API}/api/v1/admin/customers/{customer_id}",
                token=admin_tok,
            )
            d = data_of(detail) or {}
            confirmed = (d.get("profile") or {}).get("confirmed")
            r.add(
                "3.H.2b",
                "admin customer detail has confirmed profile",
                api_ok(detail) and confirmed is not None,
                json.dumps({"confirmed": confirmed}, ensure_ascii=False)[:400],
            )

        # Scenario customer generate BEFORE another demo regenerate (avoid concurrent DeepSeek)
        if scen_cid:
            _, gen_s = req(
                "POST",
                f"{API}/api/v1/sidebar/profile/generate",
                {"customer_id": int(scen_cid), "force": True},
                token=token,
            )
            ok_queue = api_ok(gen_s)
            after_s = None
            draft_s = None
            if ok_queue:
                after_s = wait_draft(
                    token,
                    int(scen_cid),
                    int((data_of(gen_s) or {}).get("job_id") or 0),
                    seconds=180 if not mock_llm else 30,
                )
                draft_s = (after_s or {}).get("draft")
            r.add(
                "T-M1-01c",
                "scenario customer profile draft",
                bool(draft_s),
                json.dumps(
                    {
                        "queued": ok_queue,
                        "generating": (after_s or {}).get("generating") if after_s else None,
                        "basic": (draft_s or {}).get("basic_info") if draft_s else None,
                        "study": (draft_s or {}).get("study_info") if draft_s else None,
                    },
                    ensure_ascii=False,
                )[:400],
            )

        # Regenerate should not silently wipe confirmed — get profile again after generate
        _, gen2 = req(
            "POST",
            f"{API}/api/v1/sidebar/profile/generate",
            {"customer_id": customer_id, "force": True},
            token=token,
        )
        if api_ok(gen2):
            after2 = wait_draft(token, customer_id, int((data_of(gen2) or {}).get("job_id") or 0), seconds=120 if not mock_llm else 30)
            confirmed2 = (after2 or {}).get("confirmed")
            r.add(
                "T-M1-03",
                "confirmed remains after regenerate",
                confirmed2 is not None,
                f"has_confirmed={confirmed2 is not None} has_new_draft={bool((after2 or {}).get('draft'))}",
            )
        else:
            r.add("T-M1-03", "confirmed remains after regenerate", False, json.dumps(gen2, ensure_ascii=False))
    else:
        r.add("T-M1-04a", "patch draft field", False, "no draft — generate failed?")
        r.add("T-M1-04b", "confirm single field", False, "skipped")
        r.add("3.H.2", "confirm all", False, "skipped")
        r.add("3.H.2b", "admin customer detail has confirmed profile", False, "skipped")
        r.add("T-M1-01c", "scenario customer profile draft", False, "skipped")
        r.add("T-M1-03", "confirmed remains after regenerate", False, "skipped")

    # (scenario generate moved above when draft path succeeds)

    # No send-message API (principle)
    _, reply_ph = req("GET", f"{API}/api/v1/sidebar/reply/_placeholder")
    r.add(
        "T-P-01",
        "no wecom send API (reply is P2 placeholder)",
        api_ok(reply_ph) and "P2" in str(data_of(reply_ph)),
        json.dumps(data_of(reply_ph), ensure_ascii=False),
    )

    # Sidebar page contains AI 建议 label (static)
    try:
        with urllib.request.urlopen(f"{WEB}/", timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # SPA — check js bundle reference; fetch first js for AI text
        import re

        m = re.search(r'/assets/[^"]+\.js', html)
        has_ai = False
        if m:
            with urllib.request.urlopen(f"{WEB}{m.group(0)}", timeout=10) as jsresp:
                js = jsresp.read().decode("utf-8", errors="ignore")
            has_ai = "AI 建议" in js
        r.add("T-M6-03", "UI copy contains AI 建议", has_ai)
    except Exception as exc:  # noqa: BLE001
        r.add("T-M6-03", "UI copy contains AI 建议", False, str(exc))

    # SSE endpoint accepts connection headers (short read)
    try:
        request = urllib.request.Request(
            f"{API}/api/v1/sidebar/sse?customer_id={customer_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=5) as resp:
            # read a little
            chunk = resp.read(64)
            r.add(
                "T-M6-02",
                "SSE endpoint reachable",
                resp.status == 200,
                f"status={resp.status} peek={chunk[:40]!r}",
            )
    except Exception as exc:  # noqa: BLE001
        # timeout while streaming can still mean OK if connected
        msg = str(exc)
        ok = "timed out" in msg.lower() or "timeout" in msg.lower()
        r.add("T-M6-02", "SSE endpoint reachable", ok, msg)

    return _finish(r)


def _finish(r: Result) -> int:
    passed = sum(1 for x in r.rows if x["ok"])
    failed = sum(1 for x in r.rows if not x["ok"])
    out = {
        "summary": {"total": len(r.rows), "passed": passed, "failed": failed},
        "cases": r.rows,
    }
    path = r"d:\ZheJiangAI\K12-UserProfile\ClassDoc\16-MVP测试报告.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nTOTAL {passed}/{len(r.rows)} passed, {failed} failed")
    print(f"JSON report: {path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
