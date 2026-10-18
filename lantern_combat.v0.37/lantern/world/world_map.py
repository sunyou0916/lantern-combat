import json
import math
from pathlib import Path

import pygame

from ..config import MIN_MAP_COLS, MIN_MAP_ROWS, PLAYER_SIZE, THEME_REGION_TILES


def load_map_size(map_path):
    with Path(map_path).open(encoding='utf-8-sig') as f:
        data = json.load(f)
    tile = int(data['tile_size'])
    cols, rows = int(data['cols']), int(data['rows'])
    if cols < MIN_MAP_COLS or rows < MIN_MAP_ROWS or tile < PLAYER_SIZE+4:
        raise ValueError('맵은 최소 32x28칸, 타일은 최소 32픽셀이어야 합니다.')
    return tile, cols, rows


class WorldMap:
    def __init__(self, tile, cols, rows, spawn, walkable, rooms, enemy_cells, traps):
        self.tile = tile
        self.cols, self.rows = cols, rows
        self.width, self.height = cols*tile, rows*tile
        self.spawn = spawn
        self.walkable = walkable
        self.rooms = rooms
        self.goals = [room.goal for room in rooms]
        self.enemy_cells = enemy_cells
        self.traps = traps
        self.visual_cells = {}
        for cell in walkable:
            nearest = min(rooms, key=lambda r: (cell[0]-r.goal[0])**2+(cell[1]-r.goal[1])**2)
            distance_sq = (cell[0]-nearest.goal[0])**2+(cell[1]-nearest.goal[1])**2
            self.visual_cells[cell] = nearest, nearest.theme if distance_sq <= THEME_REGION_TILES**2 else None

    @property
    def size(self):
        return self.width, self.height

    def center(self, cell):
        return pygame.Vector2((cell[0] + 0.5) * self.tile,
                              (cell[1] + 0.5) * self.tile)

    def cell_at(self, pos):
        return (int(pos.x//self.tile), int(pos.y//self.tile))

    def goal_rect(self, cell):
        return pygame.Rect(cell[0]*self.tile, cell[1]*self.tile, self.tile, self.tile)

    def nearest_room(self, cell):
        return min(self.rooms, key=lambda r: abs(cell[0]-r.goal[0]) + abs(cell[1]-r.goal[1]))

    def theme_for_cell(self, cell):
        return self.nearest_room(cell).theme

    def room_at(self, pos):
        return next((r for r in self.rooms if r.rect.collidepoint(pos)), None)

    def room_for_goal(self, cell):
        return next((r for r in self.rooms if r.goal == cell), None)

    def body_on_paths(self, pos, size=PLAYER_SIZE):
        half = size / 2
        for x in (pos.x-half, pos.x+half-0.001):
            for y in (pos.y-half, pos.y+half-0.001):
                if (math.floor(x/self.tile), math.floor(y/self.tile)) not in self.walkable:
                    return False
        return True

    def body_in_bounds(self, pos, size=PLAYER_SIZE):
        half = size / 2
        return half <= pos.x <= self.width-half and half <= pos.y <= self.height-half

    def nearest_walkable_center(self, pos):
        cell = min(self.walkable, key=lambda c: self.center(c).distance_squared_to(pos))
        return self.center(cell)
