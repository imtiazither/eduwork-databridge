from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileResult:
    profile: dict[str, Any]
    schema_fingerprint: str


@dataclass(frozen=True)
class DriftResult:
    status: str
    comparison: dict[str, Any]
