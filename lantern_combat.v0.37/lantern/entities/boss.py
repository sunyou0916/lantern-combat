from dataclasses import dataclass

import pygame

from ..config import BOSS_ATTACK_CHARGE, BOSS_FIRST_ATTACK_DELAY, BOSS_HP


class BossAnim:
    IDLE = 'idle'
    MOVE = 'move'
    ATTACK = 'attack'
    DASH = 'dash'


class DashPhase:
    WARNING = 'warning'
    ACTIVE = 'active'
    RECOVERY = 'recovery'


@dataclass
class BossDash:
    start: pygame.Vector2
    end: pygame.Vector2
    direction: pygame.Vector2
    distance: float
    timer: float
    travelled: float = 0.0
    phase: str = DashPhase.WARNING
    elapsed: float = 0.0
    hit: bool = False


@dataclass
class Hazard:
    pos: pygame.Vector2
    radius: float
    timer: float
    total: float
    kind: str
    effect: str
    strikes: list
    fired: bool = False
    age: float = 0.0

    @classmethod
    def lightning(cls, pos, radius, warning, kind, strikes=None):
        return cls(pos=pos.copy(), radius=radius, timer=warning, total=warning, kind=kind,
                   effect='fx_lightning_target' if kind == 'target' else 'fx_lightning_storm',
                   strikes=[p.copy() for p in strikes] if strikes else [pos.copy()])


@dataclass
class Boss:
    pos: pygame.Vector2
    hp: float = BOSS_HP
    cooldown: float = BOSS_FIRST_ATTACK_DELAY
    pattern: int = 0
    flash: float = 0.0
    anim_state: str = BossAnim.IDLE
    anim_time: float = 0.0
    moving: bool = False
    face_right: bool = True
    attack_windup: float = 0.0
    attack_kind: str = None
    dash: BossDash = None

    def set_animation(self, state):
        self.anim_state = state
        self.anim_time = 0.0

    def animation_time(self):
        time = self.anim_time
        if self.anim_state == BossAnim.ATTACK:
            windup = self.attack_windup
            time = (min(time, windup)*BOSS_ATTACK_CHARGE/windup
                    + max(0.0, time-windup))
        return time
