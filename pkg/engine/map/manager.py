import numpy as np
from pkg.engine.map.mapelement import MapElement

class MapManager:
    def __init__(self, config: dict):
        self.size = config["world"]["grid_size"]
        self.grid = np.zeros((self.size, self.size), dtype=int)
        self.elements = {}

    def set_wall(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.grid[x, y] = 1

    def add_element(self, pos, element_type, data=None):
        self.elements[pos] = MapElement(element_type, data)

    def is_wall(self, pos):
        return self.grid[pos[0], pos[1]] == 1

    def get_element(self, pos):
        return self.elements.get(pos)

    def remove_element(self, pos):
        if pos in self.elements:
            del self.elements[pos]
