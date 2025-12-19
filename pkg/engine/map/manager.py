import numpy as np
from typing import Dict, Tuple, Optional, Any, Set
from pkg.schema.models import Element

class MapManager:
    def __init__(self, config: Dict):
        self._size = config["world"]["grid_size"]
        self.grid = np.zeros((self._size, self._size), dtype=int)
        self.elements: Dict[Tuple[int, int], Element] = {}
        self._walkable_cache: Set[Tuple[int, int]] = set()

    @property
    def shape(self) -> Tuple[int, int]:
        return (self._size, self._size)

    def in_bounds(self, pos: Tuple[int, int]) -> bool:
        y, x = pos
        return 0 <= y < self._size and 0 <= x < self._size

    def set_grid(self, grid: np.ndarray):
        if grid.shape != (self._size, self._size):
            raise ValueError("Grid shape mismatch")
        self.grid = grid.astype(int)
        self._walkable_cache = {
            (int(y), int(x)) for y, x in zip(*np.where(self.grid == 0))
        }

    def is_walkable(self, pos: Tuple[int, int]) -> bool:
        return pos in self._walkable_cache

    def add_element(self, pos: Tuple[int, int], kind: str, properties: Optional[Dict[str, Any]] = None):
        if not self.in_bounds(pos):
            raise ValueError(f"Out of bounds: {pos}")
        self.elements[pos] = Element(pos=pos, kind=kind, properties=properties or {})

    def get_element(self, pos: Tuple[int, int]) -> Optional[Element]:
        return self.elements.get(pos)

    def remove_element(self, pos: Tuple[int, int]) -> bool:
        if pos in self.elements:
            del self.elements[pos]
            return True
        return False

class MapData:
    def __init__(self, grid: np.ndarray, elements: Dict[Tuple[int, int], Any]):
        self.grid = grid
        self.elements = elements
        self._h, self._w = grid.shape
        self._wall_cache = set(zip(*np.where(grid == 1)))

    def is_passable(self, pos: Tuple[int, int], ignore_walls: bool = False) -> bool:
        y, x = int(pos[0]), int(pos[1])
        if not (0 <= y < self._h and 0 <= x < self._w):
            return False
        if ignore_walls:
            return True
        return (y, x) not in self._wall_cache
