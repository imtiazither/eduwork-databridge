import re
import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    text = re.sub(r"[^\w\s@.+-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_value(field: str, value: Any) -> str:
    normalized = normalize_text(value)
    name = field.casefold()
    if "email" in name:
        return normalized.replace(" ", "")
    if "phone" in name:
        return "".join(character for character in normalized if character.isdigit())
    if name.endswith("_id") or name in {"employee_id", "record_key"}:
        return normalized.upper()
    return normalized
