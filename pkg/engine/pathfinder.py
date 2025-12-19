import heapq
import numpy as np

class Pathfinder:
    def __init__(self, grid):
        self.grid = grid
        self.height = grid.shape[0]
        self.width = grid.shape[1]

    def get_next_step(self, start, goal):
        start, goal = tuple(start), tuple(goal)
        if start == goal: return start
        path = self._astar(start, goal)
        return path[1] if len(path) > 1 else start

    def _astar(self, start, goal):
        neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        oheap = []
        heapq.heappush(oheap, (0, start))
        came_from = {}
        g_score = {start: 0}
        
        while oheap:
            current = heapq.heappop(oheap)[1]
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                return [start] + path[::-1]

            for i, j in neighbors:
                neighbor = (current[0] + i, current[1] + j)
                if not (0 <= neighbor[0] < self.height and 0 <= neighbor[1] < self.width):
                    continue
                if self.grid[neighbor[0], neighbor[1]] == 1:
                    continue
                
                tentative_g = g_score[current] + (1.414 if i != 0 and j != 0 else 1)
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self._dist(neighbor, goal)
                    heapq.heappush(oheap, (f_score, neighbor))
        return [start]

    def _dist(self, a, b):
        return np.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
