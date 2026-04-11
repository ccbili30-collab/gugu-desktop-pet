"""Bridge extension registry for gugupet_v2.

Allows registering new event handlers and intent translators
without modifying the core adapter files.
"""

from __future__ import annotations

from typing import Any, Callable

from bridge.protocol import BodyCommand, BodyState, BrainReaction


# Handler types
IntentHandler = Callable[[dict, BodyState], BodyCommand | None]


class BridgeRegistry:
    """Central registry for bridge extension points.

    Usage:
        registry = BridgeRegistry()
        registry.register_intent("my_intent", my_handler)
    """

    def __init__(self) -> None:
        self._intent_handlers: dict[str, IntentHandler] = {}
        self._event_hooks: list[Callable[[str, dict], None]] = []

    def register_intent(self, intent_name: str, handler: IntentHandler) -> None:
        """Register a handler for a new brain intent name.

        The handler receives (params, BodyState) and returns a BodyCommand or None.
        """
        self._intent_handlers[intent_name] = handler

    def register_event_hook(self, hook: Callable[[str, dict], None]) -> None:
        """Register a hook called for every incoming body event.

        Useful for logging, debugging, or side-effect triggers.
        """
        self._event_hooks.append(hook)

    def run_event_hooks(self, event_name: str, payload: dict) -> None:
        for hook in self._event_hooks:
            try:
                hook(event_name, payload)
            except Exception:
                pass

    def extra_commands(
        self, reaction: BrainReaction, body_state: BodyState
    ) -> list[BodyCommand]:
        """Generate extra body commands from registered intent handlers."""
        handler = self._intent_handlers.get(reaction.intent)
        if handler is None:
            return []
        try:
            cmd = handler(reaction.params, body_state)
            if cmd and not cmd.is_noop():
                return [cmd]
        except Exception:
            pass
        return []


# Global singleton registry — import and use this everywhere
registry = BridgeRegistry()
