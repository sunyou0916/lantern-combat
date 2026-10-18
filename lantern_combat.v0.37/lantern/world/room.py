from dataclasses import dataclass

import pygame

from ..config import PLAYER_SIZE, PURIFICATION_SECONDS, RAID_FIRST_SPAWN_DELAY, RAID_SPAWN_INSET


class RoomStatus:
    IDLE = 'idle'
    FIGHTING = 'fighting'
    CLEARED = 'cleared'
    LIGHTING = 'lighting'
    COMPLETED = 'completed'


@dataclass
class Room:
    id: int
    cells: set
    rect: pygame.Rect
    goal: tuple
    theme: str
    status: str = RoomStatus.IDLE
    purification: float = 0.0
    time_limit: float = 0.0
    time_left: float = 0.0
    spawn_timer: float = 0.0
    spawned_count: int = 0

    @property
    def completed(self):
        return self.status == RoomStatus.COMPLETED

    def start_raid(self, time_limit):
        self.status = RoomStatus.FIGHTING
        self.time_limit = time_limit
        self.time_left = time_limit
        self.spawn_timer = RAID_FIRST_SPAWN_DELAY
        self.spawned_count = 0

    def reset_raid(self):
        self.status = RoomStatus.IDLE

    def purify(self, seconds):
        self.purification = min(1.0, self.purification + seconds / PURIFICATION_SECONDS)

    def clamp(self, pos, margin=PLAYER_SIZE/2+1):
        rect = self.rect
        pos.x = max(rect.left+margin, min(rect.right-margin, pos.x))
        pos.y = max(rect.top+margin, min(rect.bottom-margin, pos.y))

    def spawn_points(self):
        rect, inset = self.rect, RAID_SPAWN_INSET
        return [pygame.Vector2(rect.left+inset, rect.top+inset),
                pygame.Vector2(rect.right-inset, rect.top+inset),
                pygame.Vector2(rect.left+inset, rect.bottom-inset),
                pygame.Vector2(rect.right-inset, rect.bottom-inset),
                pygame.Vector2(rect.centerx, rect.top+inset),
                pygame.Vector2(rect.centerx, rect.bottom-inset)]
