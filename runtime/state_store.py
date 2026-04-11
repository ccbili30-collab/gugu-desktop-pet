"""Thin JSON read/write helpers for all runtime files.

All IO goes through this module.  The rest of the codebase must not
import json and touch runtime files directly.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config import loader as cfg
from runtime.models import (
    RuntimeBridgeState,
    RuntimeCommand,
    RuntimeEventLog,
    RuntimeState,
    RuntimeStatus,
)


def _runtime_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    d = root / str(cfg.runtime().get("dir", "runtime"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rf(name: str) -> Path:
    return _runtime_dir() / name


def _read(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return default


def _write(path: Path, data: Any) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    return Path(__file__).resolve().parents[1] / "state.json"


def read_state() -> RuntimeState:
    data = _read(_state_path(), {})
    if not isinstance(data, dict):
        return RuntimeState()
    return RuntimeState.from_dict(data)


def write_state(state: RuntimeState) -> None:
    _write(_state_path(), state.to_dict())


# ---------------------------------------------------------------------------
# Body Status
# ---------------------------------------------------------------------------


def read_status() -> RuntimeStatus:
    name = str(cfg.runtime().get("status_file", "pet_action_status.json"))
    data = _read(_rf(name), {})
    if not isinstance(data, dict):
        return RuntimeStatus()
    return RuntimeStatus.from_dict(data)


def write_status(status: RuntimeStatus) -> None:
    name = str(cfg.runtime().get("status_file", "pet_action_status.json"))
    _write(_rf(name), status.to_dict())


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------


def read_event_log() -> RuntimeEventLog:
    name = str(cfg.runtime().get("event_file", "pet_action_events.json"))
    data = _read(_rf(name), {})
    if not isinstance(data, dict):
        return RuntimeEventLog()
    return RuntimeEventLog(
        next_event_id=int(data.get("next_event_id", 1) or 1),
        events=list(data.get("events", []) or []),
    )


def write_event_log(log: RuntimeEventLog) -> None:
    name = str(cfg.runtime().get("event_file", "pet_action_events.json"))
    _write(_rf(name), {"next_event_id": log.next_event_id, "events": log.events[-200:]})


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def read_command() -> RuntimeCommand:
    name = str(cfg.runtime().get("command_file", "pet_action_command.json"))
    data = _read(_rf(name), {})
    if not isinstance(data, dict):
        return RuntimeCommand()
    return RuntimeCommand(
        seq=int(data.get("seq", 0) or 0),
        action=str(data.get("action", "none") or "none"),
        params=dict(data.get("params", {}) or {}),
        source=str(data.get("source", "brain") or "brain"),
        issued_at=float(data.get("issued_at", 0.0) or 0.0),
    )


def write_command(cmd: RuntimeCommand) -> None:
    name = str(cfg.runtime().get("command_file", "pet_action_command.json"))
    _write(_rf(name), cmd.to_dict())


# ---------------------------------------------------------------------------
# Bridge state
# ---------------------------------------------------------------------------


def read_bridge_state() -> RuntimeBridgeState:
    name = str(cfg.runtime().get("bridge_file", "pet_event_bridge_state.json"))
    data = _read(_rf(name), {})
    if not isinstance(data, dict):
        return RuntimeBridgeState()
    return RuntimeBridgeState(
        agent_id=str(data.get("agent_id", "built_in") or "built_in"),
        last_event_id=int(data.get("last_event_id", 0) or 0),
    )


def write_bridge_state(state: RuntimeBridgeState) -> None:
    name = str(cfg.runtime().get("bridge_file", "pet_event_bridge_state.json"))
    _write(
        _rf(name), {"agent_id": state.agent_id, "last_event_id": state.last_event_id}
    )


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def ensure_runtime_files() -> None:
    """Create all runtime files with sane defaults if they don't exist."""
    if not _state_path().exists():
        write_state(RuntimeState())
    name_map = {
        "event_file": (
            RuntimeEventLog(),
            lambda l: {"next_event_id": l.next_event_id, "events": l.events},
        ),
        "command_file": (RuntimeCommand(), lambda c: c.to_dict()),
        "bridge_file": (
            RuntimeBridgeState(),
            lambda b: {"agent_id": b.agent_id, "last_event_id": b.last_event_id},
        ),
        "status_file": (RuntimeStatus(), lambda s: s.to_dict()),
    }
    for key, (default_obj, serialiser) in name_map.items():
        path = _rf(str(cfg.runtime().get(key, key)))
        if not path.exists():
            _write(path, serialiser(default_obj))
