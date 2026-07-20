import argparse
from pathlib import Path
from typing import cast

from eduwork_databridge.synthetic import PresetName, generate_dataset, verify_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic EduWork synthetic sources."
    )
    parser.add_argument("--preset", choices=["small", "medium", "benchmark"], default="small")
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    args = parser.parse_args()
    preset = cast(PresetName, args.preset)
    manifest = generate_dataset(args.output, preset, args.seed)
    if not verify_manifest(args.output, preset):
        raise SystemExit("Generated manifest verification failed")
    print(f"Generated {preset} synthetic dataset with seed {args.seed}: {manifest['counts']}")


if __name__ == "__main__":
    main()
