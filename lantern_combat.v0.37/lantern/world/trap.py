from dataclasses import dataclass

import pygame

from ..config import TRAP_ACTIVE_TIME, TRAP_SAFE_TIME, TRAP_WARNING_TIME


class TrapState:
    SAFE = 'safe'
    WARNING = 'warning'
    ACTIVE = 'active'


@dataclass
class Trap:
    cell: tuple
    offset: float

    def state(self, elapsed):
        cycle = TRAP_SAFE_TIME+TRAP_WARNING_TIME+TRAP_ACTIVE_TIME
        t = (elapsed+self.offset) % cycle
        if t < TRAP_SAFE_TIME:
            return TrapState.SAFE
        if t < TRAP_SAFE_TIME+TRAP_WARNING_TIME:
            return TrapState.WARNING
        return TrapState.ACTIVE

    def hit_rect(self, tile):
        x, y = self.cell
        return pygame.Rect(x*tile+4, y*tile+4, tile-8, tile-8)
