"""Run all pytest modules in isolated, offscreen Qt processes."""

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def start_worker(directory, modules, log):
    env = os.environ.copy()
    env.update(
        QT_QPA_PLATFORM="offscreen",
        WIFI_HEATMAP_RENDERER="software",
        WIFI_HEATMAP_SETTINGS_FILE=str(directory / "settings.json"),
        WIFI_HEATMAP_AP_MEMORY_FILE=str(directory / "ap.memory"),
        MPLCONFIGDIR=str(directory / "matplotlib"),
        PYTHONIOENCODING="utf-8",
        TEMP=str(directory),
        TMP=str(directory),
        TMPDIR=str(directory),
    )
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(ROOT),
               "--tb=short", "-o", "faulthandler_timeout=60", *(str(path) for path in modules)]
    return subprocess.Popen(command, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2, help="Number of parallel processes (default: 2)")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    modules = sorted((ROOT / "tests").rglob("test_*.py"))
    if not modules:
        parser.error("No test modules found")
    workers = min(args.workers, len(modules))
    start = perf_counter()
    processes = []
    with TemporaryDirectory(prefix="wifi-heatmap-tests-") as temp, ExitStack() as stack:
        try:
            for index in range(workers):
                directory = Path(temp) / f"worker-{index + 1}"
                directory.mkdir()
                log = stack.enter_context((directory / "pytest.log").open("w+b"))
                process = start_worker(directory, modules[index::workers], log)
                processes.append((process, log))
            print(f"Running {len(modules)} modules across {workers} offscreen processes.", flush=True)
            exit_codes = []
            for index, (process, log) in enumerate(processes, start=1):
                exit_codes.append(process.wait())
                log.seek(0)
                output = log.read().decode(errors="replace")
                print(f"\nWorker {index}\n{output}", end="", flush=True)
        finally:
            for process, _ in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    print(f"Total wall time: {perf_counter() - start:.2f}s", flush=True)
    return int(any(exit_codes))


if __name__ == "__main__":
    sys.exit(main())
