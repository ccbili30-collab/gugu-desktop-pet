"""Helpers for single-instance local desktop pet services."""

from __future__ import annotations

import atexit
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = BASE_DIR / "runtime"
STILL_ACTIVE = 259
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def pid_file_for(service_name: str) -> Path:
    RUNTIME_DIR.mkdir(exist_ok=True)
    return RUNTIME_DIR / f"{service_name}.pid"


def runtime_file(name: str) -> Path:
    RUNTIME_DIR.mkdir(exist_ok=True)
    return RUNTIME_DIR / name


def read_json(path: Path, default: dict | None = None) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else (default or {})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default.copy() if default else {}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False

    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False

    try:
        exit_code = wintypes.DWORD()
        if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        _kernel32.CloseHandle(handle)


class ServiceInstance:
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self.pid_file = pid_file_for(service_name)
        self.pid = os.getpid()
        self.acquired = False

    def acquire(self) -> bool:
        existing_pid = read_pid(self.pid_file)
        if existing_pid and existing_pid != self.pid and is_pid_running(existing_pid):
            return False

        self.pid_file.write_text(str(self.pid), encoding="utf-8")
        self.acquired = True
        atexit.register(self.release)
        return True

    def release(self) -> None:
        if not self.acquired:
            return

        current_pid = read_pid(self.pid_file)
        if current_pid == self.pid and self.pid_file.exists():
            self.pid_file.unlink()
        self.acquired = False


def read_pid(pid_file: Path) -> int | None:
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def ensure_single_instance(service_name: str) -> ServiceInstance | None:
    instance = ServiceInstance(service_name)
    return instance if instance.acquire() else None
