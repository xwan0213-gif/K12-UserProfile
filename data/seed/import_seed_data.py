#!/usr/bin/env python3
"""Import tag_def + script_template for OPEN-03 / Phase-2 seed data.

Usage:
  python data/seed/import_seed_data.py --base-url http://localhost:18000/api/v1 \\
      --user admin --password admin123

Requires: demo admin account, /admin/tags, /admin/script-templates (P2).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import urllib.error
    import urllib.request
except ImportError:  # pragma: no cover
    raise

ROOT = Path(__file__).resolve().parent
TAG_FILE = ROOT / "tag_def.json"
SCRIPT_FILE = ROOT / "script_template.json"


def _req(method: str, url: str, token: str | None = None, body: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> {e.code}: {detail}") from e


def login(base: str, user: str, password: str) -> str:
    # Prefer admin login path used by apps/admin
    for path in ("/auth/admin/login",):
        try:
            out = _req(
                "POST",
                f"{base.rstrip('/')}{path}",
                body={"login_name": user, "password": password},
            )
            data = out.get("data") or out
            token = data.get("access_token") or data.get("token")
            if token:
                return str(token)
        except RuntimeError:
            continue
    raise RuntimeError("admin login failed; check --base-url and credentials")


def list_tags(base: str, token: str) -> dict[str, int]:
    out = _req("GET", f"{base.rstrip('/')}/admin/tags", token=token)
    items = (out.get("data") or out).get("items") or []
    return {str(t["name"]): int(t["id"]) for t in items}


def upsert_tags(base: str, token: str, tags: list[dict]) -> tuple[int, int]:
    existing = list_tags(base, token)
    created = updated = 0
    for tag in tags:
        name = tag["name"]
        payload = {
            "name": name,
            "description": tag.get("description"),
            "is_measurable": tag.get("is_measurable", True),
            "sop_text": tag.get("sop_text"),
            "enabled": tag.get("enabled", True),
            "sort_order": tag.get("sort_order", 0),
        }
        if name in existing:
            tid = existing[name]
            _req(
                "PATCH",
                f"{base.rstrip('/')}/admin/tags/{tid}",
                token=token,
                body={
                    k: payload[k]
                    for k in (
                        "description",
                        "is_measurable",
                        "sop_text",
                        "enabled",
                        "sort_order",
                    )
                },
            )
            updated += 1
        else:
            _req("POST", f"{base.rstrip('/')}/admin/tags", token=token, body=payload)
            created += 1
    return created, updated


def try_import_scripts(base: str, token: str, scripts: list[dict]) -> str:
    path = f"{base.rstrip('/')}/admin/script-templates"
    try:
        for row in scripts:
            body = {**row}
            if body.get("stage") is None:
                body.pop("stage", None)
            _req("POST", path, token=token, body=body)
        return f"script_template imported via {path}: {len(scripts)}"
    except RuntimeError as e:
        return (
            f"script_template API not available yet (P2). JSON validated: {len(scripts)} rows "
            f"at {SCRIPT_FILE}. Detail: {e}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Import OPEN-03 seed tags/scripts")
    # Host maps API to 18000 (see deploy/docker-compose.yml); container still listens 8000.
    parser.add_argument("--base-url", default="http://localhost:18000/api/v1")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--tags-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tags = json.loads(TAG_FILE.read_text(encoding="utf-8"))
    scripts = json.loads(SCRIPT_FILE.read_text(encoding="utf-8"))
    print(f"loaded tags={len(tags)} scripts={len(scripts)}")

    if args.dry_run:
        print("dry-run ok")
        return 0

    token = login(args.base_url, args.user, args.password)
    created, updated = upsert_tags(args.base_url, token, tags)
    print(f"tags created={created} updated={updated}")

    if not args.tags_only:
        print(try_import_scripts(args.base_url, token, scripts))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
