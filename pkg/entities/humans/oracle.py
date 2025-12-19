import numpy as np
from collections import deque
from typing import Optional
from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Intent, ActionType

class Oracle(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = False
        self.mp_charge = 500
        self.max_mp_charge = 1500
        self._pathfinder = None
        self._last_grid_hash = None
        self._oni_history = {}
        self._failure_memory = {}

    def decide(self, view):
        grid = view.memory.get("grid_map")
        if grid is None: 
            return Intent(target_pos=self.pos, priority=0)

        grid_hash = hash(grid.tobytes())
        if self._pathfinder is None or self._last_grid_hash != grid_hash:
            self._pathfinder = Pathfinder(grid)
            self._last_grid_hash = grid_hash

        self._recover_mp()
        self._update_oni_history(view)

        skill_intent = self._check_skills(view)
        if skill_intent:
            return skill_intent

        onis = [a for a in view.actors if a.get("is_oni")]
        current_mp = self.mp_charge // 100

        if not onis:
            target_pos = self._find_best_cell(grid, [], search_range=5, deep_scan=False)
            priority = 10
        else:
            min_dist = min([self._l1_dist(self.pos, o["pos"]) for o in onis])
            if current_mp >= 5 and (min_dist < 8 or current_mp > 13):
                self.mp_charge -= 500
                threats = self._predict_futures_clamped(onis, grid)
                target_pos = self._find_best_cell(grid, threats, search_range=8, deep_scan=True)
                priority = 90
            else:
                target_pos = self._find_best_cell(grid, onis, search_range=6, deep_scan=False)
                priority = 50

        try:
            next_step = self._pathfinder.get_next_step(self.pos, target_pos)
            if next_step is None: raise ValueError
        except:
            next_step = self._get_emergency_step(self.pos, grid)

        return Intent(
            target_pos=tuple(map(int, next_step)), 
            priority=priority,
            action_type=ActionType.MOVE
        )

    def _check_skills(self, view) -> Optional[Intent]:
        current_mp = self.mp_charge
        onis_in_range = [a for a in view.actors if a.get("is_oni") and self._l1_dist(self.pos, a["pos"]) <= 10]
        if current_mp >= 350 and onis_in_range:
            target_oni = min(onis_in_range, key=lambda o: self._l1_dist(self.pos, o["pos"]))
            self.mp_charge -= 350
            return Intent(
                target_pos=self.pos,
                priority=100,
                action_type=ActionType.SKILL,
                metadata={
                    "skill_name": "negative_chain_reaction",
                    "target_id": target_oni["a_id"],
                    "params": {
                        "main_stamina_drain": 1.0,
                        "main_duration": 3,
                        "slow_duration": 6,
                        "chain_range": 5,
                        "chain_stamina_drain": 0.65
                    }
                }
            )

        humans_in_range = [a for a in view.actors if not a.get("is_oni") and a["a_id"] != self.a_id and self._l1_dist(self.pos, a["pos"]) <= 10]
        onis_nearby = [a for a in view.actors if a.get("is_oni") and self._l1_dist(self.pos, a["pos"]) <= 12]
        if current_mp >= 350 and humans_in_range and onis_nearby:
            self.mp_charge -= 350
            return Intent(
                target_pos=self.pos,
                priority=95,
                action_type=ActionType.SKILL,
                metadata={
                    "skill_name": "asclepius",
                    "params": {
                        "range": 10,
                        "speed_boost": 0.60,
                        "stamina_save": 0.70,
                        "duration": 10
                    }
                }
            )
        return None

    def _find_best_cell(self, grid, threats, search_range, deep_scan):
        best_pos = self.pos
        max_score = -float('inf')
        conn_depth = 6 if deep_scan else 3
        px, py = self.pos
        for dx in range(-search_range, search_range + 1):
            for dy in range(-search_range, search_range + 1):
                candidate = (px + dx, py + dy)
                if not self._is_valid(candidate, grid): continue
                max_individual_threat = 0
                for t in threats:
                    t_pos = t["pos"]
                    t_vel = t.get("vel", (0, 0))
                    dist = self._l1_dist(candidate, t_pos)
                    danger = 100 / (dist + 0.5)
                    to_cand = np.array([candidate[0]-t_pos[0], candidate[1]-t_pos[1]])
                    dot = np.dot(t_vel, to_cand) if np.linalg.norm(t_vel) > 0 else 0
                    weight = 2.5 if dot > 0 else 1.0
                    max_individual_threat = max(max_individual_threat, danger * weight)
                connectivity = self._get_connectivity(candidate, grid, depth=conn_depth)
                failure_penalty = self._failure_memory.get(candidate, 0) * 15
                score = (connectivity * 10) - (max_individual_threat * 15) - (self._l1_dist(candidate, self.pos) * 2) - failure_penalty
                if score > max_score:
                    max_score = score
                    best_pos = candidate
        return best_pos

    def _get_connectivity(self, pos, grid, depth):
        visited = {pos}
        queue = deque([(pos, 0, 1)])
        total_score = 0
        while queue:
            curr, d, weight = queue.popleft()
            if d >= depth: continue
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nxt = (curr[0]+dx, curr[1]+dy)
                if self._is_valid(nxt, grid) and nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, d + 1, weight))
                    total_score += (1.0 / (d + 1))
        return total_score

    def _get_emergency_step(self, pos, grid):
        for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
            nxt = (pos[0]+dx, pos[1]+dy)
            if self._is_valid(nxt, grid): return nxt
        return pos

    def _predict_futures_clamped(self, onis, grid):
        shadows = []
        for oni in onis:
            a_id = oni["a_id"]
            pos = np.array(oni["pos"], dtype=float)
            vel = np.array(self._oni_history.get(a_id, {}).get("vel", (0, 0)), dtype=float)
            curr = pos.copy()
            for _ in range(3):
                nxt = curr + vel
                if self._is_valid(tuple(map(int, nxt)), grid): curr = nxt
                else: break
            shadows.append({"pos": tuple(map(int, curr)), "vel": vel})
        return shadows

    def _is_valid(self, pos, grid):
        if not (0 <= pos[0] < grid.shape[0] and 0 <= pos[1] < grid.shape[1]): return False
        return grid[pos] == 0

    def _l1_dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def _recover_mp(self):
        self.mp_charge = min(self.max_mp_charge, self.mp_charge + 25)

    def _update_oni_history(self, view):
        for actor in view.actors:
            if actor.get("is_oni"):
                a_id = actor["a_id"]
                pos = tuple(map(int, actor["pos"]))
                prev = self._oni_history.get(a_id, {}).get("pos", pos)
                vel = (pos[0] - prev[0], pos[1] - prev[1])
                self._oni_history[a_id] = {"pos": pos, "vel": vel}
        if len([a for a in view.actors if a.get("is_oni") and self._l1_dist(self.pos, a["pos"]) < 3]) > 1:
            self._failure_memory[self.pos] = self._failure_memory.get(self.pos, 0) + 1
