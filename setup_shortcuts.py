"""Create desktop shortcut for Gugupet control panel.

Called by install.bat. Uses PowerShell COM (Unicode-safe).
Only creates ONE shortcut: the control panel (which can also launch the pet).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESKTOP = Path(os.path.expandvars("%USERPROFILE%")) / "Desktop"

LNK_NAME = "\u5495\u5495\u5495.lnk"
LNK_TARGET_ARGS = "pet_control_panel.pyw"
LNK_DESC = "\u5495\u5495\u684c\u5ba0\u63a7\u5236\u9762\u677f"
ICON_FILE = ROOT / "art" / "BIRD.ico"


def _get_desktop() -> Path:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        expanded = os.path.expandvars(str(val))
        p = Path(expanded)
        if p.exists():
            return p
    except Exception:
        pass
    return DESKTOP


def _create_via_powershell(desktop: Path) -> bool:
    lnk_path = desktop / LNK_NAME
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    working_dir = ROOT

    # Build PowerShell script — all Chinese is passed via subprocess stdin
    icon_arg = ""
    if ICON_FILE.exists():
        icon_arg = f"$shortcut.IconLocation = '{str(ICON_FILE)}'; "

    ps_script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{str(lnk_path)}'); "
        f"$shortcut.TargetPath = '{str(pythonw)}'; "
        f"$shortcut.Arguments = '{LNK_TARGET_ARGS}'; "
        f"$shortcut.WorkingDirectory = '{str(working_dir)}'; "
        f"$shortcut.Description = '{LNK_DESC}'; "
        f"{icon_arg}"
        "$shortcut.Save(); "
        'Write-Host "OK"'
    )

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_script,
            ],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0 and lnk_path.exists()
    except Exception as e:
        print(f"  PowerShell error: {e}")
        return False


def main() -> int:
    desktop = _get_desktop()
    print(f"  Desktop: {desktop}")

    ok = _create_via_powershell(desktop)

    if ok:
        print(f"  Shortcut created: {desktop / LNK_NAME}")
        return 0
    else:
        print("  Shortcut creation failed. Please create manually, pointing to:")
        print(f"    {ROOT / LNK_TARGET_ARGS}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
