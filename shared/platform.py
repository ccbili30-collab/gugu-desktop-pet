"""Platform-specific helpers — cross-platform wrapper.

On macOS, ctypes/wintypes are not available.
Import shared.platform_mac instead of this file on macOS,
OR use this file which now guards the Windows imports.

The mac body (pet_window_mac.py) directly imports from
shared.platform_mac, so this file only needs to work on
Windows (original behaviour unchanged).
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    import ctypes
    import hashlib
    import random
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class POINT(ctypes.Structure):
        _fields_ = [
            ("x", wintypes.LONG),
            ("y", wintypes.LONG),
        ]

    def get_work_area() -> tuple[int, int, int, int]:
        rect = RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        return rect.left, rect.top, rect.right, rect.bottom

    def get_cursor_pos() -> tuple[int, int]:
        point = POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
            return int(point.x), int(point.y)
        return 0, 0

    def generate_pet(user_id: str = "default") -> dict[str, str]:
        digest = hashlib.md5(user_id.encode()).hexdigest()
        rng = random.Random(int(digest[:8], 16))
        return {
            "name": rng.choice(
                ["咕咕", "灰灰", "小胖", "团子", "麻子", "胖嘟", "灰团", "豆豆"]
            ),
            "color": rng.choice(["#909090", "#707070", "#808080", "#A0A0A0"]),
        }

else:
    # macOS / Linux — re-export from platform_mac so any accidental
    # import of shared.platform still works.
    from shared.platform_mac import (  # noqa: F401
        RECT,
        POINT,
        get_work_area,
        get_cursor_pos,
        generate_pet,
    )
