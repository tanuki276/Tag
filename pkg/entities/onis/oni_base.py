import random
import numpy as np
from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Intent

class Oni(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.vision_range = config["entities"]["oni"]["vision_range"]
        self.confused = 0
        self.target_last_pos = None
        self.patrol_target = None
        self.search_count = 0

    def decide(self, view):
        if self.confused > 0:
            self.confused -= 1
            return Intent(target_pos=self.pos, priority=0)

        finder = Pathfinder(view.memory.get("grid_map"))
        visible_humans = [a for a in view.actors if not a["is_oni"] and a["alive"]]

        if visible_humans:
            target = min(visible_humans, key=lambda h: self._dist(self.pos, h["pos"]))
            self.target_last_pos = target["pos"]
            self.search_count = 0
        
        if self.target_last_pos:
            path = finder.get_path(self.pos, self.target_last_pos)
            next_pos = path[1] if len(path) > 1 else self.pos
            
            if self.pos == self.target_last_pos:
                self.search_count += 1
                if self.search_count > 3:
                    self.target_last_pos = None
            
            return self._create_intent(next_pos)

        if not self.patrol_target or self.pos == self.patrol_target:
            self.patrol_target = self._select_patrol_point(view)

        path = finder.get_path(self.pos, self.patrol_target)
        next_pos = path[1] if len(path) > 1 else self.pos
        
        return self._create_intent(next_pos)

    def _dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _select_patrol_point(self, view):
        grid = view.memory.get("grid_map")
        h, w = grid.shape
        for _ in range(10):
            pt = (random.randint(0, h-1), random.randint(0, w-1))
            if grid[pt] == 0:
                return pt
        return self.pos

    def _create_intent(self, target_pos):
        priority = self.config["entities"]["oni"]["move_priority"]
        if random.random() < self.config["entities"]["oni"]["dash_chance"]:
            priority += 5
        return Intent(target_pos=target_pos, priority=priority)
