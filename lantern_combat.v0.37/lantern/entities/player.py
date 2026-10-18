from dataclasses import dataclass, field

import pygame

from ..config import INITIAL_VISION_RADIUS, PLAYER_SIZE, STAGES


@dataclass
class Player:
    pos: pygame.Vector2
    max_hp: int
    damage: int
    hp: float
    vision: float
    facing: int = 1
    velocity: pygame.Vector2 = field(default_factory=pygame.Vector2)
    moving: bool = False
    side_walk: bool = False
    attack_timer: float = 0.0
    attack_buffer: float = 0.0
    hurt_timer: float = 0.0
    swing_timer: float = 0.0

    @classmethod
    def spawn(cls, pos):
        max_hp, damage, _ = STAGES[0]
        return cls(pos=pos, max_hp=max_hp, damage=damage, hp=max_hp,
                   vision=float(INITIAL_VISION_RADIUS))

    @staticmethod
    def body_at(pos):
        return pygame.Rect(round(pos.x - PLAYER_SIZE/2),
                           round(pos.y - PLAYER_SIZE/2), PLAYER_SIZE, PLAYER_SIZE)

    @property
    def rect(self):
        return self.body_at(self.pos)

    def apply_stage(self, stage):
        self.max_hp, self.damage, _ = STAGES[stage]

    def face(self, direction):
        if direction.x:
            self.facing = 1 if direction.x > 0 else -1
        self.side_walk = bool(direction.x)

    def tick_timers(self, dt):
        self.attack_timer = max(0, self.attack_timer-dt)
        self.attack_buffer = max(0, self.attack_buffer-dt)
        self.hurt_timer = max(0, self.hurt_timer-dt)
        self.swing_timer = max(0, self.swing_timer-dt)
