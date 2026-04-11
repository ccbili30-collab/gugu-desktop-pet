"""Default configuration values for gugupet_v2."""

from __future__ import annotations

DEFAULT_LLM: dict[str, object] = {
    "enabled": False,
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "timeout": 25,
    "temperature": 0.8,
    "max_tokens_reply": 260,
    "max_tokens_event": 100,
    "max_tokens_memory": 180,
}

DEFAULT_PET: dict[str, object] = {
    "name": "咕咕",
    "species": "pigeon",
    "color_override": "",  # empty = use species default palette
    "personality": {
        "boldness": 0.6,
        "sociability": 0.75,
        "playfulness": 0.8,
        "laziness": 0.25,
        "clinginess": 0.55,
    },
}

DEFAULT_DRIVES: dict[str, float] = {
    "energy": 0.72,
    "social": 0.56,
    "curiosity": 0.68,
    "comfort": 0.74,
}

DEFAULT_BRAIN: dict[str, object] = {
    "poll_interval": 0.8,  # seconds between brain loop ticks
    "autonomy_min_idle": 14.0,  # minimum idle seconds before autonomous act
    "autonomy_cooldown_min": 18.0,
    "autonomy_cooldown_max": 34.0,
}

DEFAULT_BODY: dict[str, object] = {
    "pixel_size": 6,
    "window_width": 96,
    "window_height": 96,
    "fall_gravity": 1.2,
    "terminal_velocity": 28.0,
    "air_drag": 0.995,
    "wall_bounce_factor": 0.45,
    "ground_bounce_factor": 0.35,
    "ground_bounce_min_vy": 3.0,
    "fling_max_speed": 40.0,
    "drag_velocity_blend": 0.55,
    "drag_throw_sample_window": 0.18,
    "tick_ms": 50,
}

DEFAULT_MEMORY: dict[str, object] = {
    "root": "memory",
    "max_index_chars": 1200,
    "max_context_chars": 2400,
    "max_retrieved": 3,
}

DEFAULT_RUNTIME: dict[str, object] = {
    "dir": "runtime",
    "state_file": "state.json",
    "event_file": "pet_action_events.json",
    "command_file": "pet_action_command.json",
    "status_file": "pet_action_status.json",
    "bridge_file": "pet_event_bridge_state.json",
}

DEFAULT_CONFIG: dict[str, object] = {
    "llm": DEFAULT_LLM,
    "pet": DEFAULT_PET,
    "drives": DEFAULT_DRIVES,
    "brain": DEFAULT_BRAIN,
    "body": DEFAULT_BODY,
    "memory": DEFAULT_MEMORY,
    "runtime": DEFAULT_RUNTIME,
}
