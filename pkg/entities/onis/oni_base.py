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
            # tick()とは別にdecide内でもデクリメントする二重処理を防ぐため
            # 状態更新はWorldStateに任せ、ここではIntentのみを返す
            return Intent(target_pos=self.pos, priority=0)

        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=0)

        finder = Pathfinder(grid)
        visible_humans = [a for a in view.actors if not a.get("is_oni") and a.get("alive")]

        # 視界内に人間がいる場合：追跡モード
        if visible_humans:
            target = min(visible_humans, key=lambda h: self._dist(self.pos, h["pos"]))
            self.target_last_pos = tuple(target["pos"])
            self.search_count = 0

        # 直近の目標地点がある場合：移動
        if self.target_last_pos:
            path = finder.get_path(self.pos, self.target_last_pos)
            next_pos = tuple(path[1]) if len(path) > 1 else self.pos

            if tuple(self.pos) == tuple(self.target_last_pos):
                self.search_count += 1
                if self.search_count > 3:
                    self.target_last_pos = None
            
            return self._create_intent(next_pos)

        # 目標がない場合：パトロールモード
        if not self.patrol_target or tuple(self.pos) == tuple(self.patrol_target):
            self.patrol_target = self._select_patrol_point(grid)

        path = finder.get_path(self.pos, self.patrol_target)
        next_pos = tuple(path[1]) if len(path) > 1 else self.pos

        return self._create_intent(next_pos)

    def _dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _select_patrol_point(self, grid):
        h, w = grid.shape
        walkable = np.where(grid == 0)
        if len(walkable[0]) == 0:
            return self.pos
        
        idx = random.randint(0, len(walkable[0]) - 1)
        return (int(walkable[0][idx]), int(walkable[1][idx]))

    def _create_intent(self, target_pos):
        priority = self.config["entities"]["oni"]["move_priority"]
        if random.random() < self.config["entities"]["oni"].get("dash_chance", 0.0):
            priority += 5
        return Intent(
            target_pos=tuple(target_pos), 
            priority=priority,
            metadata={"ignore_walls": False}
        )
