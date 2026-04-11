"""Update gugupet_v2 from a zip file.

No zip argument = auto-search Downloads folder, then show file picker.
Preserves user data: config.yaml, state.json, memory/, runtime/*.json
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

PRESERVE = {
    "config.yaml",
    "state.json",
    "update.bat",
    "do_update.py",
}
PRESERVE_PREFIXES = (
    "memory/",
    "runtime/",
)

INSTALL_DIR = Path(__file__).resolve().parent
ZIP_NAME = "gugupet_v2.zip"


def should_preserve(rel: str) -> bool:
    if rel in PRESERVE:
        return True
    for prefix in PRESERVE_PREFIXES:
        if rel.startswith(prefix) and rel.endswith(".json"):
            return True
    return False


def stop_pet() -> None:
    for pid_name in ("launcher", "main"):
        pid_file = INSTALL_DIR / "runtime" / f"{pid_name}.pid"
        if not pid_file.exists():
            continue
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 9)
            pid_file.unlink(missing_ok=True)
            print(f"  Stopped process {pid} ({pid_name})")
        except Exception:
            pid_file.unlink(missing_ok=True)


def find_zip_auto() -> Path | None:
    """Search common locations for gugupet_v2.zip."""
    candidates = []

    # 1. Next to this script (install dir)
    candidates.append(INSTALL_DIR / ZIP_NAME)

    # 2. Parent of install dir
    candidates.append(INSTALL_DIR.parent / ZIP_NAME)

    # 3. Downloads folder
    dl = Path(os.path.expanduser("~/Downloads"))
    if dl.exists():
        candidates.append(dl / ZIP_NAME)

    # 4. Desktop
    desktop = Path(os.path.expanduser("~/Desktop"))
    if desktop.exists():
        candidates.append(desktop / ZIP_NAME)

    for p in candidates:
        if p.exists():
            return p
    return None


def pick_zip_dialog() -> Path | None:
    """Show a file picker if auto-search failed."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Select gugupet_v2.zip",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")],
        )
        root.destroy()
        if path:
            return Path(path)
    except Exception:
        pass
    return None


def apply_update(zip_path: Path) -> None:
    print(f"Zip         : {zip_path}")
    print()

    print("[1/3] Stopping pet...")
    stop_pet()

    print("[2/3] Applying update...")
    updated = 0
    skipped = 0
    errors = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            parts = member.filename.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            rel = parts[1]

            if member.filename.endswith("/"):
                continue

            if should_preserve(rel):
                skipped += 1
                continue

            dest = INSTALL_DIR / rel
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member.filename))
                updated += 1
            except Exception as e:
                print(f"  WARN: {rel}: {e}")
                errors += 1

    print(f"  Updated {updated} files, preserved {skipped}, errors {errors}")
    print()

    if errors:
        print("[3/3] Finished with errors (see above).")
        print("      Close the pet and try again.")
    else:
        print("[3/3] Done! Restart the pet from the desktop shortcut.")


def main() -> int:
    print(f"Install dir : {INSTALL_DIR}")
    print()

    zip_path = None

    # If passed as argument, use it
    if len(sys.argv) >= 2:
        p = Path(sys.argv[1])
        if p.exists():
            zip_path = p

    # Auto-search
    if not zip_path:
        print("Searching for zip file...")
        zip_path = find_zip_auto()
        if zip_path:
            print(f"  Found: {zip_path}")

    # File picker dialog
    if not zip_path:
        print("  Not found. Opening file picker...")
        zip_path = pick_zip_dialog()

    if not zip_path or not zip_path.exists():
        print("\nNo zip file found.")
        print("Please download gugupet_v2.zip and try again,")
        print("or drag the zip file onto update.bat.")
        return 1

    apply_update(zip_path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nUpdate failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        input("\nPress Enter to close...")
