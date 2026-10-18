from dataclasses import dataclass

import pygame

from ..config import ENEMY_HP, RAID_ENEMY_FIRST_ATTACK_DELAY, RAID_ENEMY_HP


@dataclass
class Enemy:
    pos: pygame.Vector2
    hp: float
    max_hp: float
    theme: str
    room: int = None
    cooldown: float = 0.0
    flash: float = 0.0
    alert: bool = False
    path_timer: float = 0.0
    path_cell: tuple = None
    attack_anim: float = 0.0
    face_right: bool = False
    moving: bool = False

    @classmethod
    def wanderer(cls, pos, theme):
        return cls(pos=pos, hp=ENEMY_HP, max_hp=ENEMY_HP, theme=theme)

    @classmethod
    def raider(cls, pos, room):
        return cls(pos=pos, hp=RAID_ENEMY_HP, max_hp=RAID_ENEMY_HP, theme=room.theme,
                   room=room.id, cooldown=RAID_ENEMY_FIRST_ATTACK_DELAY, alert=True)

    @property
    def alive(self):
        return self.hp > 0
