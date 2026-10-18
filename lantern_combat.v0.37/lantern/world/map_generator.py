from collections import deque

import pygame

from ..config import ENEMY_COUNT, TRAP_COUNT, TRAP_SAFE_TIME
from .room import Room
from .trap import Trap
from .world_map import WorldMap

NODE_SPACING = 4
LOOP_CHANCE = 0.22
SMALL_ROOM_COUNT = 16
ROOM_THEMES = ('earth', 'water', 'sky')
MIN_SPAWN_DISTANCE = 9


def path_distances(paths, start):
    result = {start: 0}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for cell in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if cell in paths and cell not in result:
                result[cell] = result[(x, y)]+1
                queue.append(cell)
    return result


class MapGenerator:
    def __init__(self, tile, cols, rows, rng):
        self.tile, self.cols, self.rows = tile, cols, rows
        self.rng = rng

    def generate(self):
        spawn, paths = self._carve_maze()
        rooms = self._add_rooms(paths)
        distances = path_distances(paths, spawn)
        if len(distances) != len(paths):
            raise RuntimeError('전투방 연결 검사 실패')
        walkable = paths.copy()
        enemy_cells, traps = self._place_enemies_and_traps(paths, distances, rooms)
        return WorldMap(self.tile, self.cols, self.rows, spawn, walkable, rooms, enemy_cells, traps)

    def _carve_maze(self):
        rng, step = self.rng, NODE_SPACING
        nodes = [(x, y) for y in range(3, self.rows-3, step)
                 for x in range(3, self.cols-3, step)]
        node_set = set(nodes)
        map_center = pygame.Vector2(self.cols / 2, self.rows / 2)
        spawn = min(nodes, key=lambda cell: map_center.distance_to(pygame.Vector2(cell)))
        paths = {spawn}
        visited = {spawn}
        stack = [spawn]

        def carve(a, b):
            x, y = a
            dx = (b[0] > x)-(b[0] < x)
            dy = (b[1] > y)-(b[1] < y)
            paths.add((x, y))
            while (x, y) != b:
                x += dx
                y += dy
                paths.add((x, y))

        while stack:
            x, y = stack[-1]
            choices = [c for c in ((x-step, y), (x+step, y), (x, y-step), (x, y+step))
                       if c in node_set and c not in visited]
            if not choices:
                stack.pop()
                continue
            nxt = rng.choice(choices)
            carve(stack[-1], nxt)
            visited.add(nxt)
            stack.append(nxt)
        for x, y in nodes:
            for nxt in ((x+step, y), (x, y+step)):
                if nxt in node_set and rng.random() < LOOP_CHANCE:
                    carve((x, y), nxt)
        for x, y in rng.sample(nodes, min(SMALL_ROOM_COUNT, len(nodes))):
            paths.update((x+dx, y+dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        paths.update((spawn[0]+dx, spawn[1]+dy)
                     for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if len(path_distances(paths, spawn)) != len(paths):
            raise RuntimeError('랜덤 맵 연결 검증에 실패했습니다.')
        return spawn, paths

    def _add_rooms(self, paths):
        tile, rooms = self.tile, []
        anchors = [(self.cols//4, self.rows//4),
                   (self.cols*3//4, self.rows//4), (self.cols//2, self.rows*3//4)]
        for rid, (ax, ay) in enumerate(anchors):
            cx, cy = ax+self.rng.randint(-1, 1), ay+self.rng.randint(-1, 1)
            cells = {(x, y) for x in range(cx-4, cx+5) for y in range(cy-3, cy+4)}
            paths.update(cells)
            rooms.append(Room(id=rid, cells=cells,
                              rect=pygame.Rect((cx-4)*tile, (cy-3)*tile, 9*tile, 7*tile),
                              goal=(cx, cy), theme=ROOM_THEMES[rid]))
        return rooms

    def _place_enemies_and_traps(self, paths, distances, rooms):
        rng = self.rng
        goals = [room.goal for room in rooms]
        room_cells = set().union(*(r.cells for r in rooms))
        candidates = sorted(c for c in paths
                            if distances[c] >= MIN_SPAWN_DISTANCE and c not in room_cells)
        enemy_cells = rng.sample(candidates, min(ENEMY_COUNT, len(candidates)))
        reserved = set(enemy_cells) | set(goals)
        trap_cells = [c for c in candidates if c not in reserved and
                      all(abs(c[0]-g[0])+abs(c[1]-g[1]) > 2 for g in goals)]
        traps = [Trap(cell=c, offset=rng.uniform(0, TRAP_SAFE_TIME))
                 for c in rng.sample(trap_cells, min(TRAP_COUNT, len(trap_cells)))]
        return enemy_cells, traps
