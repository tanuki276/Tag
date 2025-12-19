import numpy as np

class MapData:
    def __init__(self, grid: np.ndarray, elements: dict):
        self.grid = grid
        self.elements = elements
        self.wall_positions = set(zip(*np.where(grid == 1)))

    def is_passable(self, pos, ignore_walls=False):
        y, x = int(pos[0]), int(pos[1])
        
        if not (0 <= y < self.grid.shape[0] and 0 <= x < self.grid.shape[1]):
            return False
            
        if ignore_walls:
            return True
            
        return (y, x) not in self.wall_positions
