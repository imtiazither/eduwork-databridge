import csv
import hashlib
import io
import json
import random
import re
import uuid
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from openpyxl import Workbook

from eduwork_databridge.synthetic.models import PRESETS, DatasetPreset, PresetName

FIRST_NAMES = [
    "Amina",
    "Carlos",
    "Chen",
    "Devin",
    "Elena",
    "Fatima",
    "Grace",
    "Hiro",
    "Imani",
    "Jonah",
    "Kavya",
    "Luis",
    "Maya",
    "Noah",
    "Olivia",
    "Priya",
    "Rafael",
    "Samira",
    "Theo",
    "Yuki",
]
LAST_NAMES = [
    "Adams",
    "Bennett",
    "Chen",
    "Diaz",
    "Edwards",
    "Farah",
    "Garcia",
    "Hassan",
    "Ibrahim",
    "Johnson",
    "Kim",
    "Lopez",
    "Martin",
    "Nguyen",
    "Owens",
    "Patel",
    "Rahman",
    "Singh",
    "Taylor",
    "Williams",
]
DEPARTMENTS = ["Operations", "Technology", "Sales", "Finance", "People", "Customer Success"]
COURSE_TITLES = [
    "Data Privacy Essentials",
    "Workplace Safety",
    "Customer Communication",
    "Responsible AI Foundations",
    "Manager Coaching",
    "Information Security",
    "Quality Fundamentals",
    "Project Delivery",
]
DEFECT_CATALOG = {
    "missing_employee_id": "HRIS employee identifier is blank while related systems retain an ID.",
    "name_variant": "LMS name contains spacing, punctuation, or nickname variation.",
    "duplicate_lms_account": "One synthetic person has two LMS accounts.",
    "conflicting_department": "HRIS and LMS department codes disagree.",
    "invalid_completion_status": "LMS status contains a value outside the approved code set.",
    "completion_before_assignment": "Completion timestamp precedes assignment timestamp.",
    "credential_before_assessment": "Credential award precedes the qualifying assessment.",
    "late_event": "A learning event arrives after the expected reporting window.",
    "formula_like_text": (
        "A harmless synthetic text value begins with a spreadsheet formula character."
    ),
}


def stable_uuid(seed: int, namespace: str, number: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"eduwork:{seed}:{namespace}:{number}"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_xlsx(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook(write_only=True)
    fixed_time = datetime(2026, 1, 1, tzinfo=None)
    workbook.properties.created = fixed_time
    workbook.properties.modified = fixed_time
    sheet = workbook.create_sheet("assessment_results")
    fieldnames = list(rows[0]) if rows else []
    sheet.append(fieldnames)
    for row in rows:
        sheet.append([row[field] for field in fieldnames])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    with (
        zipfile.ZipFile(buffer) as source,
        zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target,
    ):
        for name in sorted(source.namelist()):
            content = source.read(name)
            if name == "docProps/core.xml":
                content = re.sub(
                    rb"<dcterms:modified[^>]*>.*?</dcterms:modified>",
                    (
                        b'<dcterms:modified xsi:type="dcterms:W3CDTF">'
                        b"2026-01-01T00:00:00Z</dcterms:modified>"
                    ),
                    content,
                )
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            target.writestr(info, content)


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path, compression="zstd")


def _person_rows(
    seed: int, preset: DatasetPreset, rng: random.Random
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hris: list[dict[str, Any]] = []
    truth: list[dict[str, Any]] = []
    for index in range(preset.people):
        canonical_id = stable_uuid(seed, "person", index)
        employee_id = f"EMP-{index + 1:07d}"
        first = FIRST_NAMES[index % len(FIRST_NAMES)]
        last = LAST_NAMES[(index * 7) % len(LAST_NAMES)]
        department = DEPARTMENTS[index % len(DEPARTMENTS)]
        email = f"{first}.{last}.{index + 1}@example.test".lower()
        hris.append(
            {
                "employee_id": employee_id,
                "display_name": f"{first} {last}",
                "given_name": first,
                "family_name": last,
                "email": email,
                "department_code": department.upper().replace(" ", "_"),
                "employment_status": "active" if index % 17 else "leave",
                "updated_at": (
                    datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index % 180)
                ).isoformat(),
            }
        )
        truth.append(
            {
                "canonical_person_id": canonical_id,
                "employee_id": employee_id,
                "lms_user_ids": [f"LMS-{index + 1:07d}"],
                "assessment_person_id": f"ASM-{index + 1:07d}",
            }
        )
    defect_count = max(1, int(preset.people * preset.defect_rate))
    for index in rng.sample(range(preset.people), defect_count):
        hris[index]["employee_id"] = ""
    return hris, truth


def _course_rows(seed: int, count: int) -> list[dict[str, Any]]:
    return [
        {
            "course_id": f"CRS-{index + 1:05d}",
            "course_uuid": stable_uuid(seed, "course", index),
            "course_title": (
                f"{COURSE_TITLES[index % len(COURSE_TITLES)]} {index // len(COURSE_TITLES) + 1}"
            ),
            "required": index % 3 == 0,
            "credential_code": f"CERT-{index + 1:05d}" if index % 4 == 0 else "",
        }
        for index in range(count)
    ]


def _lms_rows(
    preset: DatasetPreset,
    hris: list[dict[str, Any]],
    truth: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    statuses = ["assigned", "in_progress", "completed"]
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for person_index, person in enumerate(hris):
        truth_person = truth[person_index]
        for slot in range(preset.participations_per_person):
            course = courses[(person_index * 3 + slot) % len(courses)]
            assigned = base + timedelta(days=(person_index + slot) % 120)
            status = statuses[(person_index + slot) % len(statuses)]
            completed = assigned + timedelta(days=3 + slot) if status == "completed" else None
            rows.append(
                {
                    "lms_user_id": truth_person["lms_user_ids"][0],
                    "employee_reference": person["employee_id"] or f"EMP-{person_index + 1:07d}",
                    "learner_name": person["display_name"],
                    "department": person["department_code"],
                    "course_id": course["course_id"],
                    "assignment_id": f"ASN-{person_index + 1:07d}-{slot + 1:02d}",
                    "assigned_at": assigned.isoformat(),
                    "completion_status": status,
                    "completed_at": completed.isoformat() if completed else "",
                    "progress_percent": 100
                    if status == "completed"
                    else (50 if status == "in_progress" else 0),
                    "updated_at": (assigned + timedelta(days=10)).isoformat(),
                }
            )
    variant_count = max(1, int(preset.people * preset.defect_rate))
    for person_index in rng.sample(range(preset.people), variant_count):
        row_index = person_index * preset.participations_per_person
        rows[row_index]["learner_name"] = rows[row_index]["learner_name"].replace(" ", "  ").upper()
    invalid_count = max(1, int(len(rows) * preset.defect_rate / 4))
    for row_index in rng.sample(range(len(rows)), invalid_count):
        rows[row_index]["completion_status"] = "done-ish"
    temporal_count = max(1, int(len(rows) * preset.defect_rate / 5))
    for row_index in rng.sample(range(len(rows)), temporal_count):
        assigned = datetime.fromisoformat(str(rows[row_index]["assigned_at"]))
        rows[row_index]["completed_at"] = (assigned - timedelta(days=2)).isoformat()
        rows[row_index]["completion_status"] = "completed"
    conflict_count = max(1, int(preset.people * preset.defect_rate / 3))
    for row_index in rng.sample(range(len(rows)), conflict_count):
        rows[row_index]["department"] = "CONFLICTING_UNIT"
    late_count = max(1, int(preset.people * preset.defect_rate / 4))
    for row_index in rng.sample(range(len(rows)), late_count):
        rows[row_index]["updated_at"] = datetime(2027, 1, 15, tzinfo=UTC).isoformat()
    rows[-1]["learner_name"] = "=2+2 SYNTHETIC FORMULA-LIKE TEXT"
    duplicate_count = max(1, int(preset.people * preset.duplicate_rate))
    for person_index in rng.sample(range(preset.people), duplicate_count):
        duplicate_id = f"LMS-DUP-{person_index + 1:07d}"
        truth[person_index]["lms_user_ids"].append(duplicate_id)
        source = rows[person_index * preset.participations_per_person].copy()
        source["lms_user_id"] = duplicate_id
        source["assignment_id"] = f"DUP-{source['assignment_id']}"
        rows.append(source)
    return rows


def _assessment_rows(
    preset: DatasetPreset,
    truth: list[dict[str, Any]],
    courses: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assessments: list[dict[str, Any]] = []
    credentials: list[dict[str, Any]] = []
    base = datetime(2026, 2, 1, tzinfo=UTC)
    for index, person in enumerate(truth):
        course = courses[index % len(courses)]
        assessed_at = base + timedelta(days=index % 90)
        score = 60 + (index * 13) % 41
        assessments.append(
            {
                "assessment_person_id": person["assessment_person_id"],
                "assessment_id": f"TEST-{course['course_id']}",
                "course_id": course["course_id"],
                "attempt_number": 1,
                "score": score,
                "maximum_score": 100,
                "outcome": "pass" if score >= 75 else "needs_review",
                "assessed_at": assessed_at.isoformat(),
            }
        )
        if course["credential_code"] and score >= 75:
            credentials.append(
                {
                    "assessment_person_id": person["assessment_person_id"],
                    "credential_code": course["credential_code"],
                    "awarded_at": (assessed_at + timedelta(days=1)).isoformat(),
                    "expires_at": (assessed_at + timedelta(days=366)).isoformat(),
                    "status": "active",
                }
            )
    if credentials:
        first_person = credentials[0]["assessment_person_id"]
        first_assessment = next(
            item for item in assessments if item["assessment_person_id"] == first_person
        )
        assessed_at = datetime.fromisoformat(first_assessment["assessed_at"])
        credentials[0]["awarded_at"] = (assessed_at - timedelta(days=1)).isoformat()
    return assessments, credentials


def _defect_summary(
    hris: list[dict[str, Any]],
    truth: list[dict[str, Any]],
    lms: list[dict[str, Any]],
    assessments: list[dict[str, Any]],
    credentials: list[dict[str, Any]],
) -> dict[str, int]:
    assessment_times = {
        item["assessment_person_id"]: datetime.fromisoformat(item["assessed_at"])
        for item in assessments
    }
    credential_temporal_defects = sum(
        datetime.fromisoformat(item["awarded_at"]) < assessment_times[item["assessment_person_id"]]
        for item in credentials
    )
    completion_temporal_defects = sum(
        bool(item["completed_at"])
        and datetime.fromisoformat(item["completed_at"])
        < datetime.fromisoformat(item["assigned_at"])
        for item in lms
    )
    return {
        "missing_employee_id": sum(not item["employee_id"] for item in hris),
        "name_variant": sum("  " in item["learner_name"] for item in lms),
        "duplicate_lms_account": sum(len(item["lms_user_ids"]) > 1 for item in truth),
        "conflicting_department": sum(item["department"] == "CONFLICTING_UNIT" for item in lms),
        "invalid_completion_status": sum(item["completion_status"] == "done-ish" for item in lms),
        "completion_before_assignment": completion_temporal_defects,
        "credential_before_assessment": credential_temporal_defects,
        "late_event": sum(str(item["updated_at"]).startswith("2027-") for item in lms),
        "formula_like_text": sum(
            str(item["learner_name"]).startswith(("=", "+", "-", "@")) for item in lms
        ),
    }


def generate_dataset(
    output_root: Path,
    preset_name: PresetName = "small",
    seed: int = 20260719,
) -> dict[str, Any]:
    preset = PRESETS[preset_name]
    rng = random.Random(seed)
    dataset_root = output_root / preset_name
    hris, truth = _person_rows(seed, preset, rng)
    courses = _course_rows(seed, preset.courses)
    lms = _lms_rows(preset, hris, truth, courses, rng)
    assessments, credentials = _assessment_rows(preset, truth, courses)

    files = {
        "hris_employees_csv": dataset_root / "hris" / "employees.csv",
        "lms_courses_csv": dataset_root / "lms" / "courses.csv",
        "lms_participation_json": dataset_root / "lms" / "participation.json",
        "assessment_results_xlsx": dataset_root / "assessment" / "assessment_results.xlsx",
        "credential_awards_parquet": dataset_root / "credential" / "credential_awards.parquet",
        "identity_truth_json": dataset_root / "truth" / "identity_truth.json",
    }
    write_csv(files["hris_employees_csv"], hris)
    write_csv(files["lms_courses_csv"], courses)
    write_json(files["lms_participation_json"], lms)
    write_xlsx(files["assessment_results_xlsx"], assessments)
    write_parquet(files["credential_awards_parquet"], credentials)
    write_json(files["identity_truth_json"], truth)

    manifest_files = []
    for logical_name, path in sorted(files.items()):
        manifest_files.append(
            {
                "logical_name": logical_name,
                "path": str(path.relative_to(output_root)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "project": "EduWork DataBridge",
        "synthetic": True,
        "preset": preset_name,
        "seed": seed,
        "generated_at": "2026-07-19T00:00:00+00:00",
        "preset_spec": asdict(preset),
        "counts": {
            "hris_people": len(hris),
            "lms_courses": len(courses),
            "lms_participations": len(lms),
            "assessment_results": len(assessments),
            "credential_awards": len(credentials),
            "identity_truth_rows": len(truth),
        },
        "defect_catalog": DEFECT_CATALOG,
        "defect_summary": _defect_summary(hris, truth, lms, assessments, credentials),
        "files": manifest_files,
        "privacy_notice": (
            "All records are deterministic synthetic fixtures. "
            "They do not describe real people or organizations."
        ),
    }
    manifest_path = dataset_root / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def verify_manifest(output_root: Path, preset_name: PresetName) -> bool:
    manifest_path = output_root / preset_name / "dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return all(sha256(output_root / item["path"]) == item["sha256"] for item in manifest["files"])
