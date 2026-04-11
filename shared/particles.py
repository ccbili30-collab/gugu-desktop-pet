"""Particle classes extracted from the original desktop_pet.py."""

from __future__ import annotations

import random
import time


class HeartParticle:
    def __init__(self, x: float, y: float) -> None:
        self.x = x + random.uniform(-6, 6)
        self.y = y + random.uniform(-2, 4)
        self.vx = random.uniform(-0.35, 0.35)
        self.vy = -random.uniform(1.8, 2.8)
        self.life = 1.0
        self.size = random.randint(10, 14)

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.035

    def is_alive(self) -> bool:
        return self.life > 0


class TextParticle:
    def __init__(
        self, x: float, y: float, text: str, color: str, size_range: tuple[int, int]
    ) -> None:
        self.text = text
        self.color = color
        self.x = x + random.uniform(-8, 8)
        self.y = y + random.uniform(-3, 4)
        self.vx = random.uniform(-0.25, 0.25)
        self.vy = -random.uniform(1.1, 1.9)
        self.life = 1.0
        self.size = random.randint(*size_range)

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.03

    def is_alive(self) -> bool:
        return self.life > 0


class TrailParticle:
    def __init__(
        self,
        screen_x: float,
        screen_y: float,
        color: str,
        radius: float = 3.0,
        decay: float = 0.04,
    ) -> None:
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.color = color
        self.radius = radius
        self.decay = decay
        self.life = 1.0

    def update(self) -> None:
        self.life -= self.decay

    def is_alive(self) -> bool:
        return self.life > 0.0


class SpeechBubble:
    def __init__(self, text: str, duration: float = 2.0, channel: str = "chat") -> None:
        self.text = text
        self.expires_at = time.time() + max(0.2, duration)
        self.channel = channel

    def is_alive(self) -> bool:
        return time.time() < self.expires_at
