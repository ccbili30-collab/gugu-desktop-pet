"""Control panel launcher for gugupet_v2.

Run with:
    pythonw pet_control_panel.pyw
or:
    python pet_control_panel.pyw
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ui.control_panel import main

if __name__ == "__main__":
    main()
