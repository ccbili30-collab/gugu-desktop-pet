"""gugupet_v2_mac — macOS launcher.

Starts both the body window (DesktopPetMac / pygame + pyobjc) and
the brain agent in a daemon thread, then hands off to the pygame loop.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from service_runtime import ensure_single_instance

_PID_FILE = _ROOT / "runtime" / "launcher.pid"


def _write_pid() -> None:
    _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid() -> None:
    try:
        _PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _run_brain() -> None:
    try:
        from brain.agent import run

        run()
    except Exception as exc:
        print(f"[brain] fatal: {exc}")


def main() -> None:
    instance = ensure_single_instance("launcher")
    if not instance:
        print("[launcher_mac] another instance is already running, exiting.")
        return

    _write_pid()

    # Brain runs in a daemon thread (same as Windows)
    threading.Thread(target=_run_brain, daemon=True, name="brain").start()

    try:
        from body.pet_window_mac import DesktopPetMac

        DesktopPetMac().run()
    finally:
        _remove_pid()


if __name__ == "__main__":
    main()
