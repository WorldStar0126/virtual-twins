from __future__ import annotations

import subprocess
import sys


def run(command: list[str]) -> None:
    proc = subprocess.run(command, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> None:
    run([sys.executable, "-m", "ruff", "check", "backend"])
    run([sys.executable, "-m", "unittest", "discover", "-s", "backend/tests", "-p", "test_*.py"])


if __name__ == "__main__":
    main()
