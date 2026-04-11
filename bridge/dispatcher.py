"""Bridge dispatcher for gugupet_v2.

Main brain loop calls dispatch() once per event.
Converts BodyEvent -> BrainInput -> BrainReaction -> BodyCommands.
"""

from __future__ import annotations

from bridge.command_adapter import reaction_to_commands
from bridge.event_adapter import body_state_from_runtime, event_to_brain_input
from bridge.protocol import BodyEvent, BrainReaction
from runtime.command_queue import push_command


def dispatch(
    event: BodyEvent,
    reaction: BrainReaction,
) -> None:
    """Apply a brain reaction: push body commands to the command queue."""
    body_state = body_state_from_runtime()
    commands = reaction_to_commands(reaction, body_state)
    for cmd in commands:
        if not cmd.is_noop():
            push_command(cmd.action, cmd.params, cmd.source)
