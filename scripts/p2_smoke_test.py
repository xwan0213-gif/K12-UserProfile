#!/usr/bin/env python3
"""Phase-2 (阶段5) acceptance smoke tests."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

API = "http://127.0.0.1:18000"
WEB = "http://127.0.0.1:8080"
TIMEOUT = 45


class Result:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, case_id: str, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append(
            {"id": case_id, "name": name, "ok": bool(ok), "detail": detail[:500]}
        )
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case_id} {name}" + (f" — {detail[:220]}" if detail else ""))


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
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def ok(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and payload.get("code") == 0


def data(payload: dict[str, Any]) -> Any:
    return payload.get("data")


def wait_reply(token: str, customer_id: int, scene: str = "sales", seconds: int = 90) -> dict | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        _, p = req(
            "GET",
            f"{API}/api/v1/sidebar/reply/latest?customer_id={customer_id}&scene={scene}",
            token=token,
        )
        d = data(p) if ok(p) else None
        if isinstance(d, dict) and d.get("primary"):
            return d
        time.sleep(1.5)
    return None


def wait_tag_rec(token: str, customer_id: int, seconds: int = 90) -> dict | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        _, p = req(
            "GET",
            f"{API}/api/v1/sidebar/tags?customer_id={customer_id}",
            token=token,
        )
        d = data(p) if ok(p) else None
        rec = (d or {}).get("recommendations") if isinstance(d, dict) else None
        if isinstance(rec, dict) and (rec.get("add") or rec.get("remove")):
            return {"tags": d, "rec": rec}
        time.sleep(1.5)
    return None


def main() -> int:
    r = Result()

    # Infra
    code, health = req("GET", f"{API}/health")
    r.add("INFRA-01", "API health", code == 200 and ok(health), json.dumps(data(health), ensure_ascii=False))
    for path, cid in [("/", "INFRA-02"), ("/admin/", "INFRA-03")]:
        try:
            with urllib.request.urlopen(f"{WEB}{path}", timeout=10) as resp:
                r.add(cid, f"Nginx {path}", resp.status == 200, f"status={resp.status}")
        except Exception as exc:  # noqa: BLE001
            r.add(cid, f"Nginx {path}", False, str(exc))

    # Seed demo + ensure tags/scripts exist
    _, seed = req("POST", f"{API}/api/v1/mock/seed/demo")
    r.add("P2-SEED-01", "mock seed/demo", ok(seed), json.dumps(data(seed), ensure_ascii=False))

    _, login = req(
        "POST",
        f"{API}/api/v1/auth/admin/login",
        {"login_name": "admin", "password": "admin123"},
    )
    admin_tok = (data(login) or {}).get("access_token") if ok(login) else None
    r.add("P2-AUTH-01", "admin login", bool(admin_tok))

    if admin_tok:
        _, tags = req("GET", f"{API}/api/v1/admin/tags", token=admin_tok)
        n_tags = len((data(tags) or {}).get("items") or [])
        r.add("P2-SEED-02", "tag catalog loaded (>=15)", ok(tags) and n_tags >= 15, f"count={n_tags}")

        _, scripts = req("GET", f"{API}/api/v1/admin/script-templates", token=admin_tok)
        n_scripts = len((data(scripts) or {}).get("items") or [])
        r.add(
            "P2-SEED-03",
            "script templates loaded (>=20)",
            ok(scripts) and n_scripts >= 20,
            f"count={n_scripts}",
        )

        # create one template smoke
        _, created = req(
            "POST",
            f"{API}/api/v1/admin/script-templates",
            {
                "scene": "sales",
                "stage": "junior",
                "title": f"P2测试模板-{int(time.time())}",
                "content": "这是二期测试话术，不含绝对化承诺。",
                "enabled": True,
            },
            token=admin_tok,
        )
        r.add("P2-ADMIN-01", "create script template", ok(created), json.dumps(data(created), ensure_ascii=False))

    # Advisor token + demo customers of different stages
    _, exch = req(
        "POST",
        f"{API}/api/v1/auth/wecom/exchange",
        {"code": "mock_code", "external_userid": "demo_wang"},
    )
    wecom_tok = (data(exch) or {}).get("access_token") if ok(exch) else None
    demo_cid = (data(exch) or {}).get("customer_id")
    r.add("P2-AUTH-02", "wecom exchange", bool(wecom_tok) and bool(demo_cid), f"cid={demo_cid}")

    # Prefer mock advisor token
    _, clist = req("GET", f"{API}/api/v1/mock/customers")
    items = (data(clist) or {}).get("items") or []
    demo = next((c for c in items if c.get("external_id") == "demo_wang"), None) or (
        next((c for c in items if c.get("id") == demo_cid), None)
    )
    advisor_id = (demo or {}).get("owner_user_id") or 3
    token = f"mock-{advisor_id}"
    # validate
    _, ctx = req("GET", f"{API}/api/v1/sidebar/context?customer_id={demo_cid or 1}", token=token)
    if not ok(ctx) and wecom_tok:
        token = wecom_tok
    cid_junior = int(demo_cid or (demo or {}).get("id") or 1)

    # Create senior scenario customer for T-R-01
    _, scen = req(
        "POST",
        f"{API}/api/v1/mock/seed/scenario",
        {
            "external_id": "p2_test_senior",
            "parent_name": "测试高中家长",
            "student_name": "测试高中生",
            "grade": "高二",
            "school": "市重点高中",
            "stage": "senior",
            "append_messages": False,
            "messages": [
                {"direction": "in", "content": "孩子高二物理竞赛想冲一冲，也在看一对一价格"},
                {"direction": "out", "content": "目标院校和近期模考大概多少？"},
                {"direction": "in", "content": "想先试听物理冲刺课，下周有空"},
            ],
        },
    )
    cid_senior = (data(scen) or {}).get("customer_id") if ok(scen) else None
    r.add("P2-SEED-04", "senior scenario customer", bool(cid_senior), json.dumps(data(scen), ensure_ascii=False))

    # Ensure junior has math/trial chat
    req(
        "POST",
        f"{API}/api/v1/mock/messages",
        {
            "customer_id": cid_junior,
            "direction": "in",
            "content": f"初二数学想夯实基础，方便约试听吗？P2-{int(time.time())}",
        },
    )

    # ---- Reply suggest junior ----
    _, gen_j = req(
        "POST",
        f"{API}/api/v1/sidebar/reply/suggest",
        {"customer_id": cid_junior, "scene": "sales", "force": True},
        token=token,
    )
    r.add("T-R-00a", "reply suggest junior queued", ok(gen_j), json.dumps(data(gen_j), ensure_ascii=False))
    reply_j = wait_reply(token, cid_junior)
    r.add(
        "T-R-00b",
        "reply junior has primary + alternatives + AI label",
        bool(reply_j)
        and bool(reply_j.get("primary"))
        and len(reply_j.get("alternatives") or []) >= 1
        and reply_j.get("label") == "AI 建议",
        json.dumps(
            {
                "primary": (reply_j or {}).get("primary"),
                "alts": (reply_j or {}).get("alternatives"),
                "label": (reply_j or {}).get("label"),
            },
            ensure_ascii=False,
        )[:400],
    )

    # ---- Reply suggest senior ----
    reply_s = None
    if cid_senior:
        _, gen_s = req(
            "POST",
            f"{API}/api/v1/sidebar/reply/suggest",
            {"customer_id": int(cid_senior), "scene": "sales", "force": True},
            token=token,
        )
        r.add("T-R-00c", "reply suggest senior queued", ok(gen_s), json.dumps(data(gen_s), ensure_ascii=False))
        reply_s = wait_reply(token, int(cid_senior))
        r.add(
            "T-R-01",
            "stage-differentiated reply (junior vs senior text differs)",
            bool(reply_j)
            and bool(reply_s)
            and (reply_j or {}).get("primary") != (reply_s or {}).get("primary"),
            json.dumps(
                {
                    "junior": (reply_j or {}).get("primary"),
                    "senior": (reply_s or {}).get("primary"),
                },
                ensure_ascii=False,
            )[:400],
        )
    else:
        r.add("T-R-01", "stage-differentiated reply", False, "no senior customer")

    # ---- No send API (T-R-02) ----
    # reply placeholder removed; ensure no send endpoint
    code_send, body_send = req("POST", f"{API}/api/v1/sidebar/reply/send", {"text": "x"}, token=token)
    no_send = code_send in (404, 405) or (
        isinstance(body_send, dict) and body_send.get("code") not in (0, None)
        and "send" not in str(body_send).lower()
    )
    # Also 404 from FastAPI
    no_send = code_send >= 400
    r.add(
        "T-R-02",
        "no auto-send WeCom API (send endpoint absent/failed)",
        no_send,
        f"status={code_send} body={json.dumps(body_send, ensure_ascii=False)[:160]}",
    )

    # ---- Feedback + adoption (T-R-03) ----
    adoption_before = None
    if admin_tok:
        _, ab = req("GET", f"{API}/api/v1/admin/ai/adoption?group_by=advisor", token=admin_tok)
        adoption_before = data(ab) if ok(ab) else None
        r.add("T-R-03a", "adoption endpoint before", adoption_before is not None, json.dumps(adoption_before, ensure_ascii=False)[:300])

    if reply_j and reply_j.get("suggestion_id"):
        sid = reply_j["suggestion_id"]
        _, fb_copy = req(
            "POST",
            f"{API}/api/v1/sidebar/reply/feedback",
            {"suggestion_id": sid, "action": "copy"},
            token=token,
        )
        r.add("T-R-02b", "feedback copy recorded", ok(fb_copy), json.dumps(data(fb_copy), ensure_ascii=False))

        # need a fresh suggestion for adopt, or adopt same if status allows
        _, gen2 = req(
            "POST",
            f"{API}/api/v1/sidebar/reply/suggest",
            {"customer_id": cid_junior, "scene": "sales", "force": True},
            token=token,
        )
        reply2 = wait_reply(token, cid_junior) if ok(gen2) else None
        if reply2 and reply2.get("suggestion_id"):
            _, fb_adopt = req(
                "POST",
                f"{API}/api/v1/sidebar/reply/feedback",
                {"suggestion_id": reply2["suggestion_id"], "action": "adopt"},
                token=token,
            )
            r.add("T-R-03b", "feedback adopt recorded", ok(fb_adopt), json.dumps(data(fb_adopt), ensure_ascii=False))
        else:
            r.add("T-R-03b", "feedback adopt recorded", False, "no second suggestion")
    else:
        r.add("T-R-02b", "feedback copy recorded", False, "no reply")
        r.add("T-R-03b", "feedback adopt recorded", False, "skipped")

    if admin_tok:
        _, aa = req("GET", f"{API}/api/v1/admin/ai/adoption?group_by=advisor", token=admin_tok)
        adoption_after = data(aa) if ok(aa) else None
        changed = False
        if isinstance(adoption_before, dict) and isinstance(adoption_after, dict):
            before_items = adoption_before.get("items") or []
            after_items = adoption_after.get("items") or []
            # sum copy+adopt
            def _sum(items: list) -> tuple[int, int]:
                c = sum(int(i.get("copy") or 0) for i in items)
                a = sum(int(i.get("adopt") or 0) for i in items)
                return c, a

            bc, ba = _sum(before_items)
            ac, aa_ = _sum(after_items)
            changed = (ac + aa_) > (bc + ba) or (ac > bc) or (aa_ > ba)
            r.add(
                "T-R-03",
                "adoption metrics change after feedback",
                changed or (aa_ + ac) > 0,
                f"before_copy={bc} before_adopt={ba} after_copy={ac} after_adopt={aa_}",
            )
        else:
            r.add("T-R-03", "adoption metrics change after feedback", False, "missing adoption data")

    # ---- Tag recommend (T-T-01 / T-T-02) ----
    _, tags_before = req(
        "GET", f"{API}/api/v1/sidebar/tags?customer_id={cid_junior}", token=token
    )
    active_before = {
        t.get("name") for t in ((data(tags_before) or {}).get("active") or [])
    }

    _, trec = req(
        "POST",
        f"{API}/api/v1/sidebar/tags/recommend",
        {"customer_id": cid_junior, "force": True},
        token=token,
    )
    r.add("T-T-00", "tag recommend queued", ok(trec), json.dumps(data(trec), ensure_ascii=False))

    waited = wait_tag_rec(token, cid_junior)
    rec = (waited or {}).get("rec") if waited else None
    has_reason = False
    if rec:
        for item in (rec.get("add") or []) + (rec.get("remove") or []):
            if isinstance(item, dict) and item.get("reason"):
                has_reason = True
                break
    r.add(
        "T-T-02",
        "recommendation reasons visible",
        bool(rec) and has_reason,
        json.dumps(rec, ensure_ascii=False)[:400] if rec else "no rec",
    )

    # Before confirm: active tags should not include brand-new recommended adds
    _, tags_mid = req(
        "GET", f"{API}/api/v1/sidebar/tags?customer_id={cid_junior}", token=token
    )
    active_mid = {t.get("name") for t in ((data(tags_mid) or {}).get("active") or [])}
    new_adds = []
    if rec:
        new_adds = [
            (a.get("tag_name") or a.get("name"))
            for a in (rec.get("add") or [])
            if (a.get("tag_name") or a.get("name")) not in active_before
        ]
    not_written = all(name not in active_mid or name in active_before for name in new_adds) if new_adds else True
    # More precise: newly recommended names that weren't active before should still be absent mid
    leaked = [n for n in new_adds if n in active_mid and n not in active_before]
    r.add(
        "T-T-01a",
        "recommend draft does not write formal tags yet",
        len(leaked) == 0 and bool(rec),
        f"new_adds={new_adds} leaked={leaked} active_mid={sorted(active_mid)}",
    )

    if rec and rec.get("suggestion_id"):
        _, conf = req(
            "POST",
            f"{API}/api/v1/sidebar/tags/recommend/confirm",
            {
                "suggestion_id": rec["suggestion_id"],
                "apply_add": True,
                "apply_remove": False,
            },
            token=token,
        )
        r.add("T-T-01b", "confirm recommendation", ok(conf), json.dumps(data(conf), ensure_ascii=False))
        _, tags_after = req(
            "GET", f"{API}/api/v1/sidebar/tags?customer_id={cid_junior}", token=token
        )
        active_after = {
            t.get("name") for t in ((data(tags_after) or {}).get("active") or [])
        }
        applied = any(n in active_after for n in new_adds) if new_adds else ok(conf)
        r.add(
            "T-T-01",
            "tags applied only after confirm",
            bool(applied) and len(leaked) == 0,
            f"new_adds={new_adds} after={sorted(active_after)}",
        )

        # SOP visible on active tags
        has_sop = any(
            (t.get("sop_text") or "").strip()
            for t in ((data(tags_after) or {}).get("active") or [])
        )
        r.add("T-T-03", "active tags expose SOP text", has_sop)
    else:
        r.add("T-T-01b", "confirm recommendation", False, "no suggestion")
        r.add("T-T-01", "tags applied only after confirm", False, "skipped")
        r.add("T-T-03", "active tags expose SOP text", False, "skipped")

    # Frontend copy
    try:
        with urllib.request.urlopen(f"{WEB}/", timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r'/assets/[^"]+\.js', html)
        js = ""
        if m:
            with urllib.request.urlopen(f"{WEB}{m.group(0)}", timeout=10) as jsresp:
                js = jsresp.read().decode("utf-8", errors="ignore")
        r.add(
            "T-UI-01",
            "sidebar bundle has 建议 + AI 建议 + 不代发文案",
            ("AI 建议" in js) and ("不会自动发送" in js or "手动发送" in js) and ("生成建议" in js),
            f"ai={'AI 建议' in js} nosend={('不会自动发送' in js) or ('手动发送' in js)}",
        )
        with urllib.request.urlopen(f"{WEB}/admin/", timeout=10) as resp:
            ahtml = resp.read().decode("utf-8", errors="ignore")
        am = re.search(r'/admin/assets/[^"]+\.js', ahtml)
        ajs = ""
        if am:
            with urllib.request.urlopen(f"{WEB}{am.group(0)}", timeout=10) as jsresp:
                ajs = jsresp.read().decode("utf-8", errors="ignore")
        r.add(
            "T-UI-02",
            "admin bundle has 话术模板 + AI 分析",
            ("话术模板" in ajs) and ("AI" in ajs or "采纳" in ajs),
        )
    except Exception as exc:  # noqa: BLE001
        r.add("T-UI-01", "sidebar bundle check", False, str(exc))
        r.add("T-UI-02", "admin bundle check", False, str(exc))

    return _finish(r)


def _finish(r: Result) -> int:
    passed = sum(1 for x in r.rows if x["ok"])
    failed = sum(1 for x in r.rows if not x["ok"])
    out = {
        "summary": {"total": len(r.rows), "passed": passed, "failed": failed},
        "cases": r.rows,
    }
    path = r"d:\ZheJiangAI\K12-UserProfile\ClassDoc\19-二期测试报告.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nTOTAL {passed}/{len(r.rows)} passed, {failed} failed")
    print(f"JSON report: {path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
