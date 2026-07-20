from datetime import UTC, datetime
from typing import Any

from eduwork_databridge.schemas.config import MartDefinitionConfig


class MartBuilder:
    def build(
        self,
        records: list[dict[str, Any]],
        config: MartDefinitionConfig,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        reference_time = as_of or datetime.now(UTC)
        output: list[dict[str, Any]] = []
        for record in records:
            row = {field: record.get(field) for field in config.fields}
            if config.entity == "training_participation":
                row["is_completed"] = str(record.get("status", "")) == "completed"
                row["has_progress"] = record.get("progress_percent") not in (None, "")
            elif config.entity == "credential_status":
                expires_at = record.get("expires_at")
                if expires_at:
                    parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    row["current_status"] = (
                        "expired" if parsed.astimezone(UTC) < reference_time else "active"
                    )
                else:
                    row["current_status"] = str(record.get("status", "unknown"))
            elif config.entity == "quality_trend":
                evaluated = int(record.get("evaluated", 0) or 0)
                failed = int(record.get("failed", 0) or 0)
                row["pass_rate"] = round(1 - failed / evaluated, 8) if evaluated else 1.0
            output.append(row)
        return output
