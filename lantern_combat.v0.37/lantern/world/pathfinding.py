from collections import deque
import math


class GridNavigator:

    def next_cell(self, start_pos, target_pos, walkable, tile):
        if not walkable:
            return None
        start = (int(start_pos.x // tile), int(start_pos.y // tile))
        target = (int(target_pos.x // tile), int(target_pos.y // tile))
        if start not in walkable:
            start = min(walkable, key=lambda c: self._distance(c, start_pos, tile))
        if target not in walkable:
            target = min(walkable, key=lambda c: self._distance(c, target_pos, tile))
        if start == target:
            return target
        queue = deque([start])
        previous = {start: None}
        while queue:
            cell = queue.popleft()
            if cell == target:
                break
            for nxt in ((cell[0]-1, cell[1]), (cell[0]+1, cell[1]),
                        (cell[0], cell[1]-1), (cell[0], cell[1]+1)):
                if nxt in walkable and nxt not in previous:
                    previous[nxt] = cell
                    queue.append(nxt)
        if target not in previous:
            return None
        cell = target
        while previous[cell] is not None and previous[cell] != start:
            cell = previous[cell]
        return cell

    @staticmethod
    def _distance(cell, pos, tile):
        return math.hypot((cell[0] + 0.5) * tile - pos.x,
                          (cell[1] + 0.5) * tile - pos.y)
