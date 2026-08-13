"""时间工具：与数据库无时区 datetime 字段对齐。"""

from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """当前 UTC 时间，去掉 tzinfo，便于写入 TIMESTAMP WITHOUT TIME ZONE。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
