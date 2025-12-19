import numpy as np
from typing import Dict, Tuple, Optional, Any
from pkg.schema.models import Element

class MapManager:
    def __init__(self, config: Dict):
        self._size = config["world"]["grid_size"]
        self.grid = np.zeros((self._size, self._size), dtype=int)
        self.elements: Dict[Tuple[int, int], Element] = {}

    @property
    def shape(self) -> Tuple[int, int]:
        return (self._size, self._size)

    def in_bounds(self, pos: Tuple[int, int]) -> bool:
        y, x = pos
        return 0 <= y < self._size and 0 <= x < self._size

    def is_walkable(self, pos: Tuple[int, int]) -> bool:
        if not self.in_bounds(pos):
            return False
        return self.grid[pos[0], pos[1]] == 0

    def set_grid(self, grid: np.ndarray):
        if grid.shape != (self._size, self._size):
            raise ValueError("Grid shape mismatch")
        self.grid = grid.astype(int)

    def add_element(self, pos: Tuple[int, int], kind: str, properties: Optional[Dict[str, Any]] = None):
        if not self.in_bounds(pos):
            raise ValueError(f"Position {pos} out of bounds")
        self.elements[pos] = Element(
            pos=pos, 
            kind=kind, 
            properties=properties or {}
        )

    def get_element(self, pos: Tuple[int, int]) -> Optional[Element]:
        return self.elements.get(pos)

    def remove_element(self, pos: Tuple[int, int]) -> bool:
        if pos in self.elements:
            del self.elements[pos]
            return True
        return False
