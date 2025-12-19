import random
import numpy as np
from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Intent

class Oni(BaseActor):
    shared_targets = {}
    shared_onis = {}

    @classmethod
    def reset_shared_memory(cls):
        cls.shared_targets.clear()
        cls.shared_onis.clear()

    def __init__(self, a_id, pos, config, role="CHASER"):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.role = role
        self.target_id = None
        self._pathfinder = None

    def decide(self, view):
        grid = view.memory.get("grid_map")
        if grid is None: return Intent(target_pos=self.pos, priority=0)
        
        self._update_infrastructure(view, grid)
        self._refresh_target_assignment(view)
        
        if self.target_id and self.target_id in Oni.shared_targets:
            info = Oni.shared_targets[self.target_id]
            target_pos = self._predict_and_intercept(info, grid)
            next_step = self._pathfinder.get_next_step(self.pos, target_pos)
            return Intent(target_pos=tuple(map(int, next_step)), priority=50)
        
        return Intent(target_pos=tuple(map(int, self._get_sector_patrol(grid))), priority=10)

    def _update_infrastructure(self, view, grid):
        current_turn = view.memory.get("current_turn", 0)
        self._pathfinder = Pathfinder(grid)
        
        Oni.shared_onis[self.a_id] = {"pos": self.pos, "role": self.role, "turn": current_turn}
        
        for actor in view.actors:
            a_id = actor["a_id"]
            if not actor.get("is_oni") and actor.get("alive"):
                new_pos = tuple(map(int, actor["pos"]))
                vel = (0, 0)
                if a_id in Oni.shared_targets:
                    old_pos = Oni.shared_targets[a_id]["pos"]
                    vel = (new_pos[0] - old_pos[0], new_pos[1] - old_pos[1])
                
                Oni.shared_targets[a_id] = {
                    "pos": new_pos, "vel": vel, "turn": current_turn,
                    "assigned_oni": Oni.shared_targets.get(a_id, {}).get("assigned_oni")
                }

    def _refresh_target_assignment(self, view):
        current_turn = view.memory.get("current_turn", 0)
        valid_ids = [k for k, v in Oni.shared_targets.items() if current_turn - v["turn"] < 8]

        if self.target_id not in valid_ids:
            self.target_id = None
            for tid in valid_ids:
                assigned = Oni.shared_targets[tid].get("assigned_oni")
                if not assigned or assigned not in Oni.shared_onis:
                    self.target_id = tid
                    Oni.shared_targets[tid]["assigned_oni"] = self.a_id
                    break

    def _predict_and_intercept(self, info, grid):
        t_pos = np.array(info["pos"])
        t_vel = np.array(info["vel"])
        
        if self.role == "CHASER":
            return tuple(map(int, t_pos))
        
        if self.role == "BLOCKER":
            for dist in range(4, 1, -1):
                p = t_pos + t_vel * dist
                if self._is_valid(tuple(map(int, p)), grid): return tuple(map(int, p))
            return tuple(map(int, t_pos))

        if self.role == "AMBUSHER":
            chasers = [v for k, v in Oni.shared_onis.items() if v["role"] == "CHASER"]
            if chasers:
                c_pos = np.array(chasers[0]["pos"])
                vec_from_chaser = t_pos - c_pos
                dist = np.linalg.norm(vec_from_chaser)
                if dist > 0:
                    prediction = t_pos + (vec_from_chaser / dist) * 3
                    return self._find_nearest_walkable(tuple(map(int, prediction)), grid, fallback=tuple(map(int, t_pos)))
            
            return tuple(map(int, t_pos))

    def _find_nearest_walkable(self, pos, grid, fallback):
        if self._is_valid(pos, grid): return pos
        for d in range(1, 3):
            for dx in [-d, 0, d]:
                for dy in [-d, 0, d]:
                    check = (pos[0]+dx, pos[1]+dy)
                    if self._is_valid(check, grid): return check
        return fallback

    def _is_valid(self, pos, grid):
        return (0 <= pos[0] < grid.shape[0] and 0 <= pos[1] < grid.shape[1] and grid[pos] == 0)

    def _l1_dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _get_sector_patrol(self, grid):
        walkable = np.where(grid == 0)
        if not walkable[0].size: return self.pos
        idx = random.randint(0, walkable[0].size - 1)
        return (int(walkable[0][idx]), int(walkable[1][idx]))
