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
            return self._logic_confused(view)

        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=0, metadata={})

        finder = Pathfinder(grid)
        target_pos = self._select_best_target(view)

        if target_pos:
            self.target_last_pos = tuple(target_pos)
            path = finder.get_path(self.pos, self.target_last_pos)
            next_pos = tuple(path[1]) if len(path) > 1 else self.pos
            return self._create_intent(next_pos, priority_boost=5)

        if self.target_last_pos:
            if tuple(self.pos) == self.target_last_pos:
                self.target_last_pos = None
            else:
                path = finder.get_path(self.pos, self.target_last_pos)
                next_pos = tuple(path[1]) if len(path) > 1 else self.pos
                return self._create_intent(next_pos)

        return self._create_intent(self._get_patrol_move(grid))

    def _select_best_target(self, view):
        body_targets = [a.get("body_pos") for a in view.actors if a.get("body_pos")]
        if body_targets:
            return min(body_targets, key=lambda p: self._dist(self.pos, p))

        visible_humans = [
            a for a in view.actors 
            if not a.get("is_oni") and a.get("alive") and not a.get("invincible")
        ]
        if visible_humans:
            target = min(visible_humans, key=lambda h: self._dist(self.pos, h["pos"]))
            return target["pos"]

        return None

    def _logic_confused(self, view):
        other_onis = [a for a in view.actors if a.get("is_oni") and a.get("a_id") != self.a_id]
        if other_onis:
            target = tuple(random.choice(other_onis)["pos"])
            return Intent(target_pos=target, priority=40, metadata={})
        return Intent(target_pos=self.pos, priority=0, metadata={})

    def _get_patrol_move(self, grid):
        walkable = np.where(grid == 0)
        if len(walkable[0]) == 0:
            return self.pos
        idx = random.randint(0, len(walkable[0]) - 1)
        return (int(walkable[0][idx]), int(walkable[1][idx]))

    def _dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _create_intent(self, target_pos, priority_boost=0):
        oni_cfg = self.config["entities"]["oni"]
        priority = oni_cfg["move_priority"] + priority_boost
        if random.random() < oni_cfg.get("dash_chance", 0.0):
            priority += 5
        return Intent(
            target_pos=tuple(target_pos), 
            priority=priority, 
            metadata={"ignore_walls": False}
        )
