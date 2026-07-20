import json
from pathlib import Path

from eduwork_databridge.synthetic import generate_dataset, verify_manifest


def test_small_dataset_is_deterministic_and_contains_controlled_defects(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    first = generate_dataset(left, "small", 20260719)
    second = generate_dataset(right, "small", 20260719)

    assert first["counts"] == second["counts"]
    assert first["defect_summary"] == second["defect_summary"]
    assert all(value > 0 for value in first["defect_summary"].values())
    assert [item["sha256"] for item in first["files"]] == [
        item["sha256"] for item in second["files"]
    ]
    assert verify_manifest(left, "small")
    assert verify_manifest(right, "small")


def test_seed_changes_synthetic_identity_values(tmp_path: Path) -> None:
    first = generate_dataset(tmp_path / "first", "small", 1)
    second = generate_dataset(tmp_path / "second", "small", 2)
    first_truth = next(
        item for item in first["files"] if item["logical_name"] == "identity_truth_json"
    )
    second_truth = next(
        item for item in second["files"] if item["logical_name"] == "identity_truth_json"
    )
    assert first_truth["sha256"] != second_truth["sha256"]


def test_committed_manifest_is_valid_and_explicitly_synthetic() -> None:
    root = Path("data/synthetic")
    manifest = json.loads((root / "small/dataset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["seed"] == 20260719
    assert manifest["counts"]["hris_people"] == 120
    assert verify_manifest(root, "small")
