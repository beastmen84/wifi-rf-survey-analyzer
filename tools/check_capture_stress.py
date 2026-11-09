"""Repeat the mocked native capture regression group in isolated Python processes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=8)
    options = parser.parse_args()
    if not 1 <= options.repeats <= 30:
        parser.error("--repeats must be between 1 and 30")
    out = options.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # Keep a native abort observable as an exit code, without a Windows
        # Error Reporting dialog preventing the child from terminating.
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
    results = []
    for index in range(1, options.repeats + 1):
        start = time.monotonic()
        try:
            run = subprocess.run([sys.executable, "-m", "pytest", "tests/test_guided_capture.py",
                                  "-q", "--tb=short", "--show-capture=no"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
            log = run.stdout + run.stderr
            record = dict(run=index, exit_code=run.returncode,
                          status="passed" if run.returncode == 0 else "failed")
        except subprocess.TimeoutExpired:
            log = "Capture regression process exceeded 60 seconds."
            record = dict(run=index, exit_code=None, status="timeout")
        record["seconds"] = round(time.monotonic() - start, 2)
        (out / f"capture-{index:02d}.txt").write_text(log, encoding="utf-8")
        results.append(record)
        print(f"{record['status'].upper()} capture run {index}: {record['seconds']} s", flush=True)
    (out / "capture-results.json").write_text(json.dumps(dict(
        cases=results, mocked_scanning=True, real_rf_scans=False), indent=2), encoding="utf-8")
    return 0 if all(row["status"] == "passed" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
