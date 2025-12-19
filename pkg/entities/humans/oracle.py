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

    def decide(self, view):
        if self.confused > 0:
            self.confused -= 1
            return self._logic_confused(view)

        grid = view.memory.get("grid_map")
        finder = Pathfinder(grid)
        
        target_pos = self._select_best_target(view)
        
        if target_pos:
            self.target_last_pos = target_pos
            path = finder.get_path(self.pos, target_pos)
            next_pos = path[1] if len(path) > 1 else self.pos
            return self._create_intent(next_pos, priority_boost=5)

        if self.target_last_pos:
            if self.pos == self.target_last_pos:
                self.target_last_pos = None
            else:
                path = finder.get_path(self.pos, self.target_last_pos)
                next_pos = path[1] if len(path) > 1 else self.pos
                return self._create_intent(next_pos)

        return self._create_intent(self._get_patrol_move(grid))

    def _select_best_target(self, view):
        body_targets = [a.get("body_pos") for a in view.actors if a.get("body_pos")]
        if body_targets:
            return min(body_targets, key=lambda p: self._dist(self.pos, p))

        visible_humans = [a for a in view.actors if not a["is_oni"] and a["alive"] and not a.get("invincible")]
        if visible_humans:
            target = min(visible_humans, key=lambda h: self._dist(self.pos, h["pos"]))
            return target["pos"]
        
        return None

    def _logic_confused(self, view):
        other_onis = [a for a in view.actors if a["is_oni"] and a["a_id"] != self.a_id]
        if other_onis:
            target = random.choice(other_onis)["pos"]
            return Intent(target_pos=target, priority=40)
        return Intent(target_pos=self.pos, priority=0)

    def _get_patrol_move(self, grid):
        h, w = grid.shape
        for _ in range(10):
            pt = (random.randint(0, h-1), random.randint(0, w-1))
            if grid[pt] == 0: return pt
        return self.pos

    def _dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _create_intent(self, target_pos, priority_boost=0):
        priority = self.config["entities"]["oni"]["move_priority"] + priority_boost
        if random.random() < self.config["entities"]["oni"]["dash_chance"]:
            priority += 5
        return Intent(target_pos=target_pos, priority=priority)
