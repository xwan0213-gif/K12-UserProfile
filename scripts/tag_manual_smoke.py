#!/usr/bin/env python3
import json
import urllib.error
import urllib.request

API = "http://127.0.0.1:18000"


def req(method, url, body=None, token=None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode() or "{}")


def main() -> None:
    req("POST", f"{API}/api/v1/mock/seed/demo", {})
    ex = req(
        "POST",
        f"{API}/api/v1/auth/wecom/exchange",
        {"code": "mock_code", "external_userid": "demo_wang"},
    )
    cid = (ex.get("data") or {}).get("customer_id") or 1
    tok = "mock-3"

    cat = req("GET", f"{API}/api/v1/sidebar/tags/catalog", token=tok)
    items = (cat.get("data") or {}).get("items") or []
    print("CATALOG", cat.get("code"), "n=", len(items))

    cust = req(
        "POST",
        f"{API}/api/v1/sidebar/tags/custom",
        {"customer_id": cid, "name": "侧栏自定义测", "description": "ux改进"},
        tok,
    )
    print("CUSTOM", cust.get("code"), cust.get("data"))

    tags = req("GET", f"{API}/api/v1/sidebar/tags?customer_id={cid}", token=tok)
    active = (tags.get("data") or {}).get("active") or []
    found = [t for t in active if t.get("name") == "侧栏自定义测"]
    print(
        "LIST_SOURCE",
        tags.get("code"),
        "found",
        bool(found),
        "source",
        found[0].get("source") if found else None,
    )

    if found:
        ctid = found[0]["customer_tag_id"]
        rm = req("DELETE", f"{API}/api/v1/sidebar/tags/{ctid}", token=tok)
        print("DELETE", rm.get("code"), rm.get("data"))

    if items:
        add = req(
            "POST",
            f"{API}/api/v1/sidebar/tags",
            {"customer_id": cid, "tag_id": items[0]["id"]},
            tok,
        )
        print("ADD_CATALOG", add.get("code"), add.get("data"))

    ok_all = (
        cat.get("code") == 0
        and cust.get("code") == 0
        and tags.get("code") == 0
        and bool(found)
    )
    print("RESULT", "PASS" if ok_all else "FAIL")


if __name__ == "__main__":
    main()
