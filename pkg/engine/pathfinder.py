import heapq
from collections import deque

import numpy as np


class Pathfinder:
    def __init__(self, grid):
        self.grid = grid
        self.height, self.width = grid.shape

    def _valid(self, pos):
        y, x = int(pos[0]), int(pos[1])
        return 0 <= y < self.height and 0 <= x < self.width and self.grid[y, x] == 0

    def _dist(self, a, b):
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        return dx + dy + (1.414 - 2.0) * min(dx, dy)

    def get_path(self, start, goal):
        return self._astar(tuple(start), tuple(goal))

    def get_next_step(self, start, goal):
        path = self.get_path(start, goal)
        return path[1] if len(path) > 1 else tuple(start)

    def _astar(self, start, goal):
        start, goal = tuple(start), tuple(goal)
        if not self._valid(start) or not self._valid(goal):
            return [start]
        if start == goal:
            return [start]

        heap = [(0.0, start)]
        came_from = {}
        g_score = {start: 0.0}
        closed = set()

        while heap:
            _, current = heapq.heappop(heap)
            if current in closed:
                continue
            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                return list(reversed(path))

            closed.add(current)
            for dy, dx in ((0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
                nxt = (current[0] + dy, current[1] + dx)
                if not self._valid(nxt) or nxt in closed:
                    continue
                if dy and dx:
                    if not self._valid((current[0] + dy, current[1])):
                        continue
                    if not self._valid((current[0], current[1] + dx)):
                        continue
                    cost = 1.414
                else:
                    cost = 1.0
                tentative = g_score[current] + cost
                if tentative < g_score.get(nxt, float("inf")):
                    came_from[nxt] = current
                    g_score[nxt] = tentative
                    heapq.heappush(heap, (tentative + self._dist(nxt, goal), nxt))
        return [start]

    def has_los(self, start, end):
        y0, x0 = map(int, start)
        y1, x1 = map(int, end)
        dy, dx = abs(y1 - y0), abs(x1 - x0)
        sy = 1 if y0 < y1 else -1
        sx = 1 if x0 < x1 else -1
        err = dx - dy
        y, x = y0, x0
        while True:
            if not (0 <= y < self.height and 0 <= x < self.width):
                return False
            if (y, x) not in {(y0, x0), (y1, x1)} and self.grid[y, x] == 1:
                return False
            if (y, x) == (y1, x1):
                return True
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def generate_dijkstra_map(self, goal):
        distances = np.full(self.grid.shape, np.inf, dtype=float)
        goal = tuple(map(int, goal))
        if not self._valid(goal):
            return distances
        distances[goal] = 0.0
        queue = deque([goal])
        while queue:
            y, x = queue.popleft()
            base = distances[y, x]
            for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
                nxt = (y + dy, x + dx)
                if self._valid(nxt) and distances[nxt] > base + 1:
                    distances[nxt] = base + 1
                    queue.append(nxt)
        return distances

    def get_safe_direction(self, start, threats, distance=8):
        start = tuple(map(int, start))
        threats = [tuple(map(int, p)) for p in threats]
        if not threats:
            return start
        best, best_score = start, -float("inf")
        sy, sx = start
        for y in range(max(0, sy-distance), min(self.height, sy+distance+1)):
            for x in range(max(0, sx-distance), min(self.width, sx+distance+1)):
                candidate = (y, x)
                if not self._valid(candidate):
                    continue
                path = self._astar(start, candidate)
                if len(path) <= 1 and candidate != start:
                    continue
                threat_dist = min(self._dist(candidate, t) for t in threats)
                mobility = sum(self._valid((y+dy, x+dx)) for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)))
                score = threat_dist + mobility * 0.35 - max(0, len(path)-1) * 0.15
                if score > best_score:
                    best_score, best = score, candidate
        return best
