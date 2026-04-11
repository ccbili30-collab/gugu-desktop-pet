"""
fix_deps.py — 检查并自动补全咕咕桌宠所需依赖
独立运行，不影响 install.bat。
用法: python fix_deps.py
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

# (import_name, pip_package, min_version_attr)
REQUIRED = [
    ("PIL", "Pillow>=10.0.0", "__version__"),
    ("yaml", "PyYAML>=6.0", "__version__"),
    ("tkinter", None, None),  # stdlib, cannot pip-install
]

ROOT = Path(__file__).resolve().parent
REQ_FILE = ROOT / "requirements.txt"


def _check(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def _install(pip_spec: str) -> bool:
    print(f"  正在安装 {pip_spec} ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pip_spec, "--quiet"],
        capture_output=False,
    )
    return result.returncode == 0


def main() -> None:
    print("=" * 48)
    print("  咕咕桌宠 — 依赖检查工具")
    print("=" * 48)
    print()

    missing: list[str] = []
    ok: list[str] = []
    stdlib_missing: list[str] = []

    for import_name, pip_spec, _ in REQUIRED:
        if _check(import_name):
            ok.append(import_name)
            print(f"  [OK]  {import_name}")
        else:
            if pip_spec is None:
                stdlib_missing.append(import_name)
                print(f"  [!!]  {import_name}  (内置模块缺失，请重装 Python)")
            else:
                missing.append(pip_spec)
                print(f"  [缺失] {import_name}  -> 需要 {pip_spec}")

    print()

    if stdlib_missing:
        print("警告: 以下内置模块缺失，pip 无法修复，请重新安装 Python 3.10+:")
        for m in stdlib_missing:
            print(f"  - {m}")
        print()

    if not missing:
        print("所有依赖已就绪，无需安装。")
        print()
        input("按 Enter 退出...")
        return

    print(f"发现 {len(missing)} 个缺失依赖，开始自动安装...")
    print()

    # Upgrade pip silently first
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        capture_output=True,
    )

    failed: list[str] = []
    for spec in missing:
        if _install(spec):
            print(f"  [完成] {spec}")
        else:
            failed.append(spec)
            print(f"  [失败] {spec}")

    print()
    if failed:
        print("以下依赖安装失败，请检查网络连接后重试:")
        for f in failed:
            print(f"  - {f}")
        print()
        print("也可手动运行:")
        for f in failed:
            print(f'  python -m pip install "{f}"')
    else:
        print("全部依赖安装成功！")

    print()
    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
