from dataclasses import dataclass
from typing import Literal

PresetName = Literal["small", "medium", "benchmark"]


@dataclass(frozen=True)
class DatasetPreset:
    people: int
    courses: int
    participations_per_person: int
    duplicate_rate: float
    defect_rate: float


PRESETS: dict[PresetName, DatasetPreset] = {
    "small": DatasetPreset(
        people=120,
        courses=6,
        participations_per_person=3,
        duplicate_rate=0.05,
        defect_rate=0.08,
    ),
    "medium": DatasetPreset(
        people=2_000,
        courses=18,
        participations_per_person=6,
        duplicate_rate=0.04,
        defect_rate=0.06,
    ),
    "benchmark": DatasetPreset(
        people=100_000,
        courses=80,
        participations_per_person=10,
        duplicate_rate=0.03,
        defect_rate=0.05,
    ),
}
