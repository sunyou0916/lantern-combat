from dataclasses import dataclass

import pygame

from ..config import FLAME_RANGE, FLAME_SPEED


@dataclass
class Flame:
    pos: pygame.Vector2
    direction: pygame.Vector2
    damage: float
    distance: float = 0.0

    def advance(self, dt):
        step = FLAME_SPEED * dt
        self.pos += self.direction * step
        self.distance += step

    @property
    def spent(self):
        return self.distance >= FLAME_RANGE


@dataclass
class HealItem:
    pos: pygame.Vector2
    room: int = None
