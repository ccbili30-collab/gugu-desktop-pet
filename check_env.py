"""Quick environment check for Gugupet V2.

Run this before first launch if the app does not start.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def check_module(name: str) -> bool:
    try:
        importlib.import_module(name)
        print(f"OK    module: {name}")
        return True
    except Exception as exc:
        print(f"FAIL  module: {name} -> {exc}")
        return False


def check_path(path: str) -> bool:
    p = ROOT / path
    ok = p.exists()
    print(f"{'OK   ' if ok else 'FAIL '} path: {p}")
    return ok


def main() -> None:
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version.split()[0]}")
    print()

    ok = True
    ok &= check_module("PIL")
    ok &= check_module("yaml")
    ok &= check_path("config.yaml")
    ok &= check_path("state.json")
    ok &= check_path("runtime")
    ok &= check_path("memory")
    ok &= check_path("body/pet_window.py")
    ok &= check_path("pet_control_panel.pyw")
    ok &= check_path("start.bat")

    print()
    if ok:
        print("Environment looks OK.")
    else:
        print("Environment check failed. Fix the missing items above first.")
        sys.exit(1)


if __name__ == "__main__":
    main()
