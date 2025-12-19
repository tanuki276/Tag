import numpy as np
from pkg.engine.map.mapelement import MapElement

class MapManager:
    def __init__(self, config: dict):
        self.size = config["world"]["grid_size"]
        self.grid = np.zeros((self.size, self.size), dtype=int)
        self.elements = {}

    def set_wall(self, y, x):
        if 0 <= y < self.size and 0 <= x < self.size:
            self.grid[y, x] = 1

    def add_element(self, pos, element_type, data=None):
        pos = tuple(map(int, pos))
        if 0 <= pos[0] < self.size and 0 <= pos[1] < self.size:
            self.elements[pos] = MapElement(element_type, data)

    def is_wall(self, pos):
        y, x = map(int, pos)
        if not (0 <= y < self.size and 0 <= x < self.size):
            return True
        return self.grid[y, x] == 1

    def get_element(self, pos):
        return self.elements.get(tuple(map(int, pos)))

    def remove_element(self, pos):
        pos = tuple(map(int, pos))
        if pos in self.elements:
            del self.elements[pos]
            return True
        return False
