from __future__ import annotations


def build_authorization_header(raw_value: str) -> dict[str, str]:
    value = raw_value.strip()
    if not value:
        return {}
    return {"Authorization": value}


def mask_secret(value: str) -> str:
    clean = value.strip()
    if not clean:
        return ""
    if len(clean) <= 8:
        return "****"
    return f"{clean[:4]}...{clean[-4:]}"