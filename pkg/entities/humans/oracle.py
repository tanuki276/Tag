from collections import deque

import numpy as np

from pkg.entities.humans.human_base import Human
from pkg.schema.models import ActionType, Intent, Priority


class Oracle(Human):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.job = "ORACLE"
        oracle_cfg = config["entities"].get("oracle", {})
        self.vision_range = oracle_cfg.get("vision_range", max(10, self.vision_range))
        self.mp_charge = oracle_cfg.get("initial_mp", 500)
        self.max_mp_charge = oracle_cfg.get("max_mp", 1500)
        self.mp_recover = oracle_cfg.get("mp_recover", 25)
        self._oni_history = {}
        self._failure_memory = {}

    def decide(self, view):
        if self.stun > 0:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT), action_type=ActionType.STAY)
        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT))
        self._update_knowledge(view, grid)
        self._update_oni_history(view)
        skill = self._check_skills(view)
        if skill is not None:
            return skill
        onis = [a for a in view.actors if a.is_oni and a.alive]
        if not onis:
            return super().decide(view)
        min_dist = min(self._l1(self.pos, o.pos) for o in onis)
        threats = self._predict_futures(onis, grid) if min_dist < 8 else [{"pos": o.pos, "vel": (0,0)} for o in onis]
        target = self._find_best_cell(grid, threats, search_range=8 if min_dist < 8 else 6)
        use_dash = self.stamina >= self.dash_cost and min_dist < 8
        return Intent(target_pos=target, priority=int(Priority.URGENT if min_dist < 8 else Priority.SKILL_MID), metadata={"dash": use_dash, "stamina_cost": self.dash_cost if use_dash else self.walk_cost})

    def _check_skills(self, view):
        onis = [a for a in view.actors if a.is_oni and a.alive]
        allies = [a for a in view.actors if not a.is_oni and a.alive and a.a_id != self.a_id]
        if self.mp_charge >= 700 and onis and len(allies) >= 2:
            return Intent(target_pos=self.pos, priority=int(Priority.SKILL_HIGH), action_type=ActionType.SKILL, metadata={"skill_name": "asclepius", "mp_cost": 350, "params": {"range": 10, "speed_boost": 0.60, "stamina_save": 0.70, "duration": 10}})
        onis_in_range = [o for o in onis if self._l1(self.pos, o.pos) <= 10]
        if self.mp_charge >= 350 and onis_in_range:
            target = min(onis_in_range, key=lambda o: self._l1(self.pos, o.pos))
            return Intent(target_pos=self.pos, priority=int(Priority.URGENT), action_type=ActionType.SKILL, metadata={"skill_name": "negative_chain_reaction", "target_id": target.a_id, "mp_cost": 350, "params": {"slow_duration": 6, "chain_range": 5}})
        return None

    def _find_best_cell(self, grid, threats, search_range):
        best, best_score = self.pos, -float("inf")
        y0, x0 = self.pos
        for y in range(max(0,y0-search_range), min(grid.shape[0], y0+search_range+1)):
            for x in range(max(0,x0-search_range), min(grid.shape[1], x0+search_range+1)):
                if grid[y, x] != 0:
                    continue
                candidate = (y, x)
                danger = max((100.0/(self._l1(candidate, t["pos"])+0.5) for t in threats), default=0.0)
                score = self._connectivity(candidate, grid, 4)*8 - danger*10 - self._l1(candidate, self.pos) - self._failure_memory.get(candidate,0)*15
                if score > best_score:
                    best_score, best = score, candidate
        return best

    def _connectivity(self, pos, grid, depth):
        visited = {pos}
        queue = deque([(pos, 0)])
        score = 0.0
        while queue:
            current, d = queue.popleft()
            if d >= depth:
                continue
            for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
                nxt = (current[0]+dy, current[1]+dx)
                if 0 <= nxt[0] < grid.shape[0] and 0 <= nxt[1] < grid.shape[1] and grid[nxt] == 0 and nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, d+1))
                    score += 1.0/(d+1)
        return score

    def _predict_futures(self, onis, grid):
        shadows = []
        for oni in onis:
            pos = np.array(oni.pos, dtype=int)
            vel = np.array(self._oni_history.get(oni.a_id, {}).get("vel", (0,0)), dtype=int)
            curr = pos.copy()
            for _ in range(3):
                nxt = curr + vel
                p = tuple(map(int, nxt))
                if 0 <= p[0] < grid.shape[0] and 0 <= p[1] < grid.shape[1] and grid[p] == 0:
                    curr = nxt
                else:
                    break
            shadows.append({"pos": tuple(map(int, curr)), "vel": tuple(map(int, vel))})
        return shadows

    def _update_oni_history(self, view):
        nearby = 0
        for actor in view.actors:
            if not actor.is_oni:
                continue
            prev = self._oni_history.get(actor.a_id, {}).get("pos", actor.pos)
            vel = (actor.pos[0]-prev[0], actor.pos[1]-prev[1])
            self._oni_history[actor.a_id] = {"pos": actor.pos, "vel": vel}
            if self._l1(self.pos, actor.pos) < 3:
                nearby += 1
        if nearby > 1:
            self._failure_memory[self.pos] = self._failure_memory.get(self.pos, 0) + 1

    @staticmethod
    def _l1(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def tick(self):
        super().tick()
        self.mp_charge = min(self.max_mp_charge, self.mp_charge + self.mp_recover)
