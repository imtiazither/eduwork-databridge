from pathlib import Path

from eduwork_databridge.synthetic import PresetName, verify_manifest


def main() -> None:
    root = Path("data/synthetic")
    candidates: tuple[PresetName, ...] = ("small", "medium")
    presets = [name for name in candidates if (root / name).exists()]
    if not presets:
        raise SystemExit("No committed synthetic dataset presets were found")
    failed = [name for name in presets if not verify_manifest(root, name)]
    if failed:
        raise SystemExit("Synthetic manifest verification failed: " + ", ".join(failed))
    print("Verified synthetic presets: " + ", ".join(presets))


if __name__ == "__main__":
    main()
