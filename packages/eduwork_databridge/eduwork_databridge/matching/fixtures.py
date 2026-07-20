import csv
import json
import uuid
from pathlib import Path
from typing import Any


def load_synthetic_identity_fixture(
    dataset_root: Path,
    organization_id: uuid.UUID,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    with (dataset_root / "hris/employees.csv").open(encoding="utf-8", newline="") as handle:
        hris = list(csv.DictReader(handle))
    lms = json.loads((dataset_root / "lms/participation.json").read_text(encoding="utf-8"))
    truth_rows = json.loads(
        (dataset_root / "truth/identity_truth.json").read_text(encoding="utf-8")
    )
    records: list[dict[str, Any]] = []
    truth: dict[str, str] = {}
    for index, (person, identity_truth) in enumerate(zip(hris, truth_rows, strict=True)):
        record_key = f"hris-row:{index + 1}"
        records.append(
            {
                "organization_id": str(organization_id),
                "record_key": record_key,
                "source": "hris",
                "employee_id": person["employee_id"],
                "display_name": person["display_name"],
                "email": person["email"],
                "organization_unit_key": person["department_code"],
            }
        )
        truth[record_key] = identity_truth["canonical_person_id"]
    first_lms_record: dict[str, dict[str, Any]] = {}
    for participation in lms:
        first_lms_record.setdefault(str(participation["lms_user_id"]), participation)
    truth_by_lms = {
        lms_user_id: row["canonical_person_id"]
        for row in truth_rows
        for lms_user_id in row["lms_user_ids"]
    }
    for lms_user_id, participation in sorted(first_lms_record.items()):
        record_key = f"lms:{lms_user_id}"
        records.append(
            {
                "organization_id": str(organization_id),
                "record_key": record_key,
                "source": "lms",
                "employee_id": participation["employee_reference"],
                "display_name": participation["learner_name"],
                "email": "",
                "organization_unit_key": participation["department"],
            }
        )
        truth[record_key] = truth_by_lms[lms_user_id]
    return records, truth
