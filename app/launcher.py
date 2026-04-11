"""gugupet_v2 full launcher.

Starts both the body window and the brain agent in parallel.
Body runs in the main thread (Tkinter requirement).
Brain runs in a daemon thread.
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
        return
    _write_pid()

    # Start brain in background thread
    brain_thread = threading.Thread(target=_run_brain, daemon=True, name="brain")
    brain_thread.start()

    try:
        from body.pet_window import DesktopPet

        DesktopPet().run()
    finally:
        _remove_pid()


if __name__ == "__main__":
    main()
