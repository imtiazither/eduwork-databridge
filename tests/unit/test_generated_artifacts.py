import subprocess
import sys


def test_committed_generated_artifacts_are_current() -> None:
    for script in ["scripts/export_json_schemas.py", "scripts/generate_data_dictionary.py"]:
        subprocess.run([sys.executable, script, "--check"], check=True)
    subprocess.run([sys.executable, "scripts/verify_synthetic_data.py"], check=True)
