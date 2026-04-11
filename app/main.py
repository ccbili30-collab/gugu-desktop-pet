"""gugupet_v2 body launcher — runs the original DesktopPet directly.

Also starts the brain daemon thread so AI works regardless of entry point.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from service_runtime import ensure_single_instance
from body.pet_window import DesktopPet


def _run_brain() -> None:
    try:
        from brain.agent import run

        run()
    except Exception as exc:
        print(f"[brain] fatal: {exc}")


def main() -> None:
    instance = ensure_single_instance("main")
    if instance:
        brain_thread = threading.Thread(target=_run_brain, daemon=True, name="brain")
        brain_thread.start()
        DesktopPet().run()


if __name__ == "__main__":
    main()
