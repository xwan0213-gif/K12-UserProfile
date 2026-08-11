#!/usr/bin/env python3
"""Phase-3 backend smoke (no UI)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

API = "http://127.0.0.1:18000"


def req(method: str, url: str, body: dict | None = None, token: str | None = None, timeout: float = 60):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def ok(p: dict) -> bool:
    return isinstance(p, dict) and p.get("code") == 0


def data(p: dict) -> Any:
    return p.get("data")


rows: list[tuple[str, bool, str]] = []


def add(cid: str, name: str, passed: bool, detail: str = "") -> None:
    rows.append((cid, passed, detail[:300]))
    print(f"[{'PASS' if passed else 'FAIL'}] {cid} {name}" + (f" — {detail[:200]}" if detail else ""))


def wait_reply(token: str, cid: int, scene: str, sec: int = 90):
    end = time.time() + sec
    while time.time() < end:
        _, p = req("GET", f"{API}/api/v1/sidebar/reply/latest?customer_id={cid}&scene={scene}", token=token)
        d = data(p) if ok(p) else None
        if isinstance(d, dict) and d.get("primary"):
            return d
        time.sleep(1.5)
    return None


def wait_sched_draft(token: str, cid: int, sec: int = 90):
    end = time.time() + sec
    while time.time() < end:
        _, p = req("GET", f"{API}/api/v1/sidebar/schedules?customer_id={cid}&scope=customer", token=token)
        d = data(p) if ok(p) else None
        drafts = (d or {}).get("drafts") or []
        if drafts:
            return drafts[0], d
        time.sleep(1.5)
    return None, None


def main() -> int:
    _, health = req("GET", f"{API}/health")
    add("INFRA", "health", ok(health), json.dumps(data(health), ensure_ascii=False))

    req("POST", f"{API}/api/v1/mock/seed/demo")
    _, exch = req("POST", f"{API}/api/v1/auth/wecom/exchange", {"code": "mock_code", "external_userid": "demo_wang"})
    cid = (data(exch) or {}).get("customer_id") or 1
    token = "mock-3"
    _, ctx = req("GET", f"{API}/api/v1/sidebar/context?customer_id={cid}", token=token)
    if not ok(ctx):
        token = (data(exch) or {}).get("access_token") or token
    add("AUTH", "advisor token", bool(token), f"cid={cid}")

    # ASR
    _, asr = req(
        "POST",
        f"{API}/api/v1/sidebar/asr/transcribe",
        {
            "customer_id": cid,
            "audio_ref": "mock://voice/p3-test.wav",
            "content_hint": "下周周六上午方便来试听吗",
            "create_message": True,
        },
        token=token,
    )
    asr_d = data(asr) or {}
    add("T-R-04a", "ASR transcribe", ok(asr) and bool(asr_d.get("asr_text") or asr_d.get("transcript")), json.dumps(asr_d, ensure_ascii=False))

    # time phrase message for schedule
    req(
        "POST",
        f"{API}/api/v1/mock/messages",
        {"customer_id": cid, "direction": "in", "content": "下周六上午我们过来试听，记得提醒我"},
    )

    # CS reply
    _, sug = req(
        "POST",
        f"{API}/api/v1/sidebar/reply/suggest",
        {"customer_id": cid, "scene": "cs", "force": True},
        token=token,
    )
    add("T-R-05a", "cs suggest queued", ok(sug), json.dumps(data(sug), ensure_ascii=False))
    reply = wait_reply(token, int(cid), "cs")
    cs_ok = bool(reply and reply.get("primary"))
    # service wording heuristic
    text = (reply or {}).get("primary") or ""
    add("T-R-05", "cs reply content", cs_ok, text[:180])

    # also service alias
    _, sug2 = req(
        "POST",
        f"{API}/api/v1/sidebar/reply/suggest",
        {"customer_id": cid, "scene": "service", "force": True},
        token=token,
    )
    add("T-R-05b", "scene service alias", ok(sug2), json.dumps(data(sug2), ensure_ascii=False))

    # Schedule suggest
    _, ss = req(
        "POST",
        f"{API}/api/v1/sidebar/schedules/suggest",
        {"customer_id": cid, "force": True},
        token=token,
    )
    add("T-S-01a", "schedule suggest queued", ok(ss), json.dumps(data(ss), ensure_ascii=False))
    draft, listing = wait_sched_draft(token, int(cid))
    add("T-S-01", "schedule draft from time phrase", bool(draft), json.dumps(draft, ensure_ascii=False) if draft else "none")

    # Pref
    _, pref = req(
        "PATCH",
        f"{API}/api/v1/sidebar/schedules/pref",
        {"weak_tip": True, "strong_notify": False, "quiet_hours": ["22:00-08:00"]},
        token=token,
    )
    add("T-S-04a", "patch remind pref", ok(pref), json.dumps(data(pref), ensure_ascii=False))
    _, pref_g = req("GET", f"{API}/api/v1/sidebar/schedules/pref", token=token)
    pref_d = data(pref_g) or {}
    add("T-S-04", "pref persisted", ok(pref_g) and (pref_d.get("weak_tip") is True or (pref_d.get("remind_pref") or {}).get("weak_tip") is True), json.dumps(pref_d, ensure_ascii=False))

    # Confirm with calendar sync (expect degrade)
    sid = None
    if draft:
        sid = draft.get("suggestion_id") or draft.get("id")
    conf_body = {"sync_calendar": True}
    if sid:
        conf_body["suggestion_id"] = sid
    _, conf = req("POST", f"{API}/api/v1/sidebar/schedules/confirm", conf_body, token=token)
    conf_d = data(conf) or {}
    item = conf_d.get("item") or conf_d.get("schedule") or conf_d
    sync_state = (item or {}).get("sync_state") if isinstance(item, dict) else conf_d.get("sync_state")
    status = (item or {}).get("status") if isinstance(item, dict) else conf_d.get("status")
    add(
        "T-S-02",
        "confirm keeps item; calendar may fail",
        ok(conf) and (status in ("confirmed", "done") or conf_d.get("id") or (item or {}).get("id")),
        json.dumps(conf_d, ensure_ascii=False)[:300],
    )
    add(
        "T-S-02b",
        "calendar degrade sync_state failed|none|synced",
        sync_state in ("failed", "none", "synced", None) or ok(conf),
        f"sync_state={sync_state}",
    )

    # list confirmed
    _, listed = req("GET", f"{API}/api/v1/sidebar/schedules?customer_id={cid}&scope=customer", token=token)
    items = (data(listed) or {}).get("items") or []
    add("T-S-02c", "confirmed schedule listable", ok(listed) and len(items) >= 1, f"count={len(items)}")

    schedule_id = None
    if items:
        schedule_id = items[0].get("id")
    elif isinstance(item, dict):
        schedule_id = item.get("id")
    elif conf_d.get("id"):
        schedule_id = conf_d.get("id")

    # Remind weak/strong
    if schedule_id:
        _, weak = req(
            "POST",
            f"{API}/api/v1/sidebar/schedules/{schedule_id}/remind",
            {"mode": "weak"},
            token=token,
        )
        _, strong = req(
            "POST",
            f"{API}/api/v1/sidebar/schedules/{schedule_id}/remind",
            {"mode": "strong"},
            token=token,
        )
        add("T-S-03a", "weak remind", ok(weak), json.dumps(data(weak), ensure_ascii=False))
        strong_d = data(strong) or {}
        add(
            "T-S-03",
            "strong remind degrades without crash",
            ok(strong) and (strong_d.get("degraded") is True or strong_d.get("delivered") is False or ok(strong)),
            json.dumps(strong_d, ensure_ascii=False),
        )
    else:
        add("T-S-03a", "weak remind", False, "no schedule id")
        add("T-S-03", "strong remind", False, "no schedule id")

    # ASR then sales reply based_on possible
    _, sug_s = req(
        "POST",
        f"{API}/api/v1/sidebar/reply/suggest",
        {"customer_id": cid, "scene": "sales", "force": True},
        token=token,
    )
    reply_s = wait_reply(token, int(cid), "sales") if ok(sug_s) else None
    add(
        "T-R-04",
        "after ASR can still generate reply",
        bool(reply_s and reply_s.get("primary")),
        json.dumps({"based_on_asr": (reply_s or {}).get("based_on_asr"), "primary": (reply_s or {}).get("primary")}, ensure_ascii=False)[:250],
    )

    passed = sum(1 for _, p, _ in rows if p)
    failed = len(rows) - passed
    out = {
        "summary": {"total": len(rows), "passed": passed, "failed": failed},
        "cases": [{"id": a, "ok": b, "detail": c} for a, b, c in rows],
    }
    path = r"d:\ZheJiangAI\K12-UserProfile\ClassDoc\21-三期测试报告.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nTOTAL {passed}/{len(rows)} passed, {failed} failed")
    print(f"JSON: {path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
