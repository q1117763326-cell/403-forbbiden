import re

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
