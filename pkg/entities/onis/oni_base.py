import numpy as np

from pkg.engine.pathfinder import Pathfinder
from pkg.entities.actor import BaseActor
from pkg.schema.models import ActionType, Intent, Priority


class Oni(BaseActor):
    def __init__(self, a_id, pos, config, role="CHASER"):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.role = role
        self.vision_range = config["entities"]["oni"]["vision_range"]

    def decide(self, view):
        if self.confused > 0:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT), action_type=ActionType.STAY)
        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT))
        humans = [a for a in view.actors if not a.is_oni and a.alive and not a.escaped]
        target = None
        if humans:
            target = min(humans, key=lambda h: self._l1(self.pos, h.pos))
            predicted = self._predict_target(target.a_id, target.pos, view.memory)
        else:
            remembered = self._latest_remembered_human(view.memory)
            if remembered is not None:
                predicted = remembered
            else:
                return Intent(target_pos=self._patrol(grid, view.memory.get("current_turn", 0)), priority=int(Priority.WAIT))
        finder = Pathfinder(grid)
        if self.role == "CHASER" and target is not None:
            destination = target.pos
        elif self.role == "BLOCKER":
            destination = self._block_position(predicted, grid, finder)
        elif self.role == "AMBUSHER":
            destination = self._ambush_position(predicted, grid)
        else:
            destination = predicted
        return Intent(target_pos=destination, priority=int(Priority.SKILL_HIGH if target is not None else Priority.MOVE_DEFAULT), action_type=ActionType.MOVE, metadata={"target_id": target.a_id if target is not None else None})

    def _predict_target(self, target_id, current_pos, memory):
        history = memory.get("prediction_map", {}).get(target_id, [])
        if len(history) >= 2:
            prev, last = np.array(history[-2]), np.array(history[-1])
            velocity = np.clip(last-prev, -1, 1)
            return tuple(map(int, last + velocity*2))
        return tuple(current_pos)

    def _latest_remembered_human(self, memory):
        seen = [info for info in memory.get("actors", {}).values() if not info.get("is_oni") and info.get("pos") is not None]
        return tuple(max(seen, key=lambda info: info.get("last_turn", -1))["pos"]) if seen else None

    def _block_position(self, predicted, grid, finder):
        py, px = predicted
        dmap = finder.generate_dijkstra_map(self._nearest_valid((py, px), grid))
        best, best_score = self._nearest_valid((py, px), grid), float("inf")
        for radius in range(1, 6):
            for dy, dx in ((radius,0),(-radius,0),(0,radius),(0,-radius)):
                p = (py+dy, px+dx)
                if not self._valid(p, grid):
                    continue
                score = dmap[p] + self._connectivity(p, grid)*2
                if score < best_score:
                    best_score, best = score, p
        return best

    def _ambush_position(self, predicted, grid):
        py, px = predicted
        best, best_score = self._nearest_valid((py, px), grid), float("inf")
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                p = (py+dy, px+dx)
                if self._valid(p, grid):
                    score = self._connectivity(p, grid) + 0.2*self._l1(p, predicted)
                    if score < best_score:
                        best_score, best = score, p
        return best

    def _patrol(self, grid, turn):
        rng = np.random.default_rng((hash(self.a_id)+int(turn)) & 0xFFFFFFFF)
        for _ in range(30):
            y, x = int(rng.integers(0, grid.shape[0])), int(rng.integers(0, grid.shape[1]))
            if grid[y, x] == 0:
                return (y, x)
        return self.pos

    @staticmethod
    def _valid(p, grid):
        return 0 <= p[0] < grid.shape[0] and 0 <= p[1] < grid.shape[1] and grid[p] == 0

    def _nearest_valid(self, p, grid):
        if self._valid(p, grid):
            return p
        for radius in range(1, max(grid.shape)):
            for dy in range(-radius, radius+1):
                for dx in (-radius, radius):
                    q = (p[0]+dy, p[1]+dx)
                    if self._valid(q, grid): return q
            for dx in range(-radius+1, radius):
                for dy in (-radius, radius):
                    q = (p[0]+dy, p[1]+dx)
                    if self._valid(q, grid): return q
        return self.pos

    @staticmethod
    def _connectivity(p, grid):
        return sum(0 <= p[0]+dy < grid.shape[0] and 0 <= p[1]+dx < grid.shape[1] and grid[p[0]+dy, p[1]+dx] == 0 for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)))

    @staticmethod
    def _l1(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])
