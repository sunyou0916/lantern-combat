import pygame

from ..config import ZOOM_MAX, ZOOM_MIN, ZOOM_STEP


class Camera:
    def __init__(self, pos):
        self.pos = pos
        self.zoom = 1.0
        self.follow = True

    def follow_target(self, pos):
        self.follow = True
        self.pos = pos.copy()

    def zoom_by(self, steps):
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom*(ZOOM_STEP**steps)))

    def pan(self, delta, player_pos, world_size):
        if self.follow:
            self.pos = player_pos.copy()
        self.follow = False
        self.pos -= pygame.Vector2(delta)/self.zoom
        self.pos.x = max(0, min(world_size[0], self.pos.x))
        self.pos.y = max(0, min(world_size[1], self.pos.y))

    @staticmethod
    def view_origin(focus, view_size, world_size):
        (view_w, view_h), (world_w, world_h) = view_size, world_size
        return pygame.Vector2(
            max(0, min(focus.x-view_w/2, world_w-view_w)) if view_w < world_w else (world_w-view_w)/2,
            max(0, min(focus.y-view_h/2, world_h-view_h)) if view_h < world_h else (world_h-view_h)/2)
