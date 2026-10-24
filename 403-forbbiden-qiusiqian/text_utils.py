import re
from datetime import date, datetime, timezone

_EMAIL_PATTERN = re.compile(r"^([^\s@]+)@([^\s@]+\.[^\s@]+)$")


def mask_email(email):
    """Mask an email for display, e.g. alice@xmu.edu.my -> a***@xmu.edu.my."""
    if not isinstance(email, str):
        return ""
    value = email.strip()
    match = _EMAIL_PATTERN.fullmatch(value)
    if not match:
        return ""
    local, domain = match.groups()
    return f"{local[0]}***@{domain}"


def _to_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_relative_time(value):
    """Format a SQLite/ISO timestamp as a friendly relative time.

    Invalid values are returned unchanged so the card can still show the raw
    timestamp instead of failing.
    """
    parsed = _to_datetime(value)
    if parsed is None:
        return value if isinstance(value, str) else ""

    seconds = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60} 分钟前"
    if seconds < 86400:
        return f"{seconds // 3600} 小时前"
    return f"{seconds // 86400} 天前"
