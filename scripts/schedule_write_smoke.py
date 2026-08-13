#!/usr/bin/env python3
"""阶段 B 日程写路径冒烟：手工创建 / PATCH / confirm.edits / dismiss / pref quiet_hours。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

API = "http://127.0.0.1:8000/api/v1"


def req(method: str, url: str, body: dict | None = None, token: str | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return resp.status, payload.get("data", payload)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> {e.code}: {detail}") from e


def main() -> int:
    print("== schedule write-path smoke ==")
    _, auth = req(
        "POST",
        f"{API}/auth/wecom/exchange",
        {"code": "mock_code", "external_userid": "demo_wang"},
    )
    token = auth["access_token"]
    cid = auth.get("customer_id")
    if not cid:
        _, customers = req("GET", f"{API}/mock/customers", token=token)
        cid = (customers.get("items") or [{}])[0].get("id")
    assert cid, "no customer_id"
    print(f"customer_id={cid}")

    start = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0).isoformat()

    # B.1 create
    _, created = req(
        "POST",
        f"{API}/sidebar/schedules",
        {
            "customer_id": cid,
            "title": "冒烟手工待办",
            "start_at": start,
            "priority": "high",
            "remark": "smoke",
            "sync_calendar": False,
        },
        token=token,
    )
    sid = created["id"]
    assert created["title"] == "冒烟手工待办"
    assert created["status"] == "confirmed"
    print(f"PASS create id={sid}")

    # B.2 patch title/time then done
    new_start = (datetime.utcnow() + timedelta(days=2)).replace(microsecond=0).isoformat()
    _, patched = req(
        "PATCH",
        f"{API}/sidebar/schedules/{sid}",
        {"title": "冒烟已改标题", "start_at": new_start, "priority": "medium"},
        token=token,
    )
    assert patched["title"] == "冒烟已改标题"
    print("PASS patch fields")

    _, done = req(
        "PATCH",
        f"{API}/sidebar/schedules/{sid}",
        {"status": "done"},
        token=token,
    )
    assert done["status"] == "done"
    print("PASS patch done")

    # seed a schedule suggestion via pipeline is heavy; insert via suggest then dismiss
    # Prefer create a fake suggestion through confirm path: use suggest + list drafts
    req(
        "POST",
        f"{API}/sidebar/schedules/suggest",
        {"customer_id": cid, "force": True},
        token=token,
    )
    draft = None
    for _ in range(25):
        _, listed = req(
            "GET",
            f"{API}/sidebar/schedules?customer_id={cid}&scope=customer",
            token=token,
        )
        drafts = listed.get("drafts") or []
        if drafts:
            draft = drafts[0]
            break
        import time

        time.sleep(0.8)

    if draft:
        # B.3 confirm with edits
        edit_start = (datetime.utcnow() + timedelta(days=3)).replace(microsecond=0).isoformat()
        _, conf = req(
            "POST",
            f"{API}/sidebar/schedules/confirm",
            {
                "suggestion_id": draft["suggestion_id"],
                "sync_calendar": False,
                "edits": {
                    "title": "确认前已改标题",
                    "start_at": edit_start,
                    "priority": "low",
                    "remark": "edits-smoke",
                },
            },
            token=token,
        )
        assert conf["title"] == "确认前已改标题"
        assert conf["status"] == "confirmed"
        print(f"PASS confirm.edits id={conf['id']}")

        # another suggest for dismiss
        req(
            "POST",
            f"{API}/sidebar/schedules/suggest",
            {"customer_id": cid, "force": True},
            token=token,
        )
        draft2 = None
        for _ in range(25):
            _, listed = req(
                "GET",
                f"{API}/sidebar/schedules?customer_id={cid}&scope=customer",
                token=token,
            )
            drafts = listed.get("drafts") or []
            if drafts:
                draft2 = drafts[0]
                break
            import time

            time.sleep(0.8)
        if draft2:
            _, dismissed = req(
                "POST",
                f"{API}/sidebar/schedules/dismiss",
                {"suggestion_id": draft2["suggestion_id"]},
                token=token,
            )
            assert dismissed["status"] == "rejected"
            print(f"PASS dismiss suggestion_id={draft2['suggestion_id']}")
        else:
            print("SKIP dismiss (no second draft)")
    else:
        print("SKIP confirm.edits / dismiss (no draft from suggest — check LLM/mock)")

    # B.4 quiet_hours
    _, pref = req(
        "PATCH",
        f"{API}/sidebar/schedules/pref",
        {
            "weak_tip": True,
            "strong_notify": False,
            "quiet_hours": ["22:00-08:00"],
        },
        token=token,
    )
    assert pref.get("quiet_hours") == ["22:00-08:00"]
    print("PASS pref quiet_hours")

    print("ALL PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
