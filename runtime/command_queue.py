"""Command queue helpers for gugupet_v2.

The brain writes commands; the body reads and executes them.
"""

from __future__ import annotations

import time
from typing import Any

from bridge.protocol import BodyCommand, BodyCommandAction
from runtime.state_store import read_command, write_command
from runtime.models import RuntimeCommand


def push_command(
    action: str,
    params: dict[str, Any] | None = None,
    source: str = "brain",
) -> int:
    """Write a command for the body to execute.  Returns the seq number."""
    current = read_command()
    seq = max(1, int(current.seq or 0) + 1)
    cmd = RuntimeCommand(
        seq=seq,
        action=action,
        params=params or {},
        source=source,
        issued_at=time.time(),
    )
    write_command(cmd)
    return seq


def pop_command(last_seq: int) -> BodyCommand | None:
    """Body calls this.  Returns new command if seq changed, else None."""
    current = read_command()
    if int(current.seq or 0) <= last_seq:
        return None
    return BodyCommand(
        seq=int(current.seq),
        action=str(current.action or BodyCommandAction.NONE),
        params=dict(current.params or {}),
        source=str(current.source or "brain"),
    )
