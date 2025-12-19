import random
import numpy as np
from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Intent

class Human(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = False
        self.is_human = True
        self.vision_range = config["entities"]["human"]["vision_range"]
        self.has_doll = config["entities"]["human"]["initial_dolls"] > 0
        self.stun = 0
        self.known_exit = None
        self.exploration_map = None
        self.target_node = None
        self.stuck_counter = 0

    def decide(self, view):
        if self.stun > 0:
            return Intent(target_pos=self.pos, priority=0)

        grid = view.memory.get("grid_map")
        finder = Pathfinder(grid)
        self._update_knowledge(view, grid)

        onis = [a for a in view.actors if a.get("is_oni")]
        if onis:
            self.target_node = None 
            oni_pos = [o["pos"] for o in onis]
            next_pos = finder.get_safe_direction(self.pos, oni_pos, distance=8)
            return Intent(target_pos=next_pos, priority=self.config["entities"]["human"]["move_priority"] + 5)

        if self.known_exit:
            path = finder.get_path(self.pos, self.known_exit)
            if len(path) > 1:
                return Intent(target_pos=path[1], priority=self.config["entities"]["human"]["move_priority"] + 2)

        visible_keys = [pos for pos, el in view.elements if "KEY" in el.type.name]
        if visible_keys:
            target_key = min(visible_keys, key=lambda p: abs(p[0]-self.pos[0]) + abs(p[1]-self.pos[1]))
            path = finder.get_path(self.pos, target_key)
            if len(path) > 1:
                return Intent(target_pos=path[1], priority=self.config["entities"]["human"]["move_priority"] + 1)

        if not self.target_node or self.pos == self.target_node or self.stuck_counter > 5:
            self.target_node = self._select_next_frontier(grid)
            self.stuck_counter = 0

        path = finder.get_path(self.pos, self.target_node)
        if len(path) > 1:
            next_pos = path[1]
            if next_pos == self.prev_pos:
                self.stuck_counter += 1
            return Intent(target_pos=next_pos, priority=self.config["entities"]["human"]["move_priority"])

        self.target_node = None
        return Intent(target_pos=self.pos, priority=0)

    def _update_knowledge(self, view, grid):
        if self.exploration_map is None:
            self.exploration_map = np.zeros_like(grid)
        
        self.exploration_map[self.pos[0], self.pos[1]] += 1
        
        for pos, el in view.elements:
            if el.type.name == "EXIT":
                self.known_exit = pos

    def _select_next_frontier(self, grid):
        h, w = grid.shape
        candidates = []
        for _ in range(15):
            tx, ty = random.randint(0, h-1), random.randint(0, w-1)
            if grid[tx, ty] == 0:
                score = self.exploration_map[tx, ty]
                candidates.append(((tx, ty), score))
        
        if not candidates:
            return self.pos
        return min(candidates, key=lambda x: x[1])[0]
