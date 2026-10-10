import numpy as np

from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import ActionType, Intent, Priority


class Human(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = False
        self.is_human = True
        self.vision_range = config["entities"]["human"]["vision_range"]
        self.has_doll = config["entities"]["human"].get("initial_dolls", 0) > 0
        self.stamina = 100
        self.max_stamina = 100
        self.dash_cost = 10
        self.walk_cost = 2
        self.recover_rate = 5
        self.stamina_rate = 1.0
        self.asclepius_active = False
        self.asclepius_duration = 0
        self.known_exit = None
        self.exploration_map = None
        self.target_node = None
        self.stuck_counter = 0
        self.pending_keys = []
        self.keys_identified = 0

    def decide(self, view):
        if self.stun > 0:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT), action_type=ActionType.STAY)
        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT))
        finder = Pathfinder(grid)
        self._update_knowledge(view, grid)
        onis = [a for a in view.actors if a.is_oni and a.alive]
        base_priority = int(self.config["entities"]["human"]["move_priority"])
        if onis:
            self.target_node = None
            target_pos = finder.get_safe_direction(self.pos, [o.pos for o in onis], distance=8)
            use_dash = self.stamina >= self.dash_cost
            return Intent(target_pos=target_pos, priority=base_priority+30, action_type=ActionType.MOVE, metadata={"dash": use_dash, "stamina_cost": self.dash_cost if use_dash else self.walk_cost})
        if view.memory.get("exit_open") and self.known_exit is not None:
            return Intent(target_pos=self.known_exit, priority=base_priority+10, metadata={"stamina_cost": self.walk_cost})
        visible_keys = [e for e in view.elements if e.kind == "KEY"]
        if visible_keys:
            target = min(visible_keys, key=lambda e: abs(e.pos[0]-self.pos[0]) + abs(e.pos[1]-self.pos[1]))
            return Intent(target_pos=target.pos, priority=base_priority+5, metadata={"stamina_cost": self.walk_cost})
        if self.target_node is None or tuple(self.pos) == tuple(self.target_node) or self.stuck_counter > 5:
            self.target_node = self._select_next_frontier(grid, view.memory.get("current_turn", 0))
            self.stuck_counter = 0
        if self.target_node is None:
            return Intent(target_pos=self.pos, priority=base_priority)
        path = finder.get_path(self.pos, self.target_node)
        if len(path) <= 1:
            self.stuck_counter += 1
            self.target_node = None
            return Intent(target_pos=self.pos, priority=base_priority)
        return Intent(target_pos=self.target_node, priority=base_priority, metadata={"stamina_cost": self.walk_cost})

    def _update_knowledge(self, view, grid):
        if self.exploration_map is None:
            self.exploration_map = np.zeros_like(grid, dtype=np.int32)
        y, x = self.pos
        self.exploration_map[y, x] += 1
        for element in view.elements:
            if element.kind == "EXIT":
                self.known_exit = tuple(element.pos)

    def _select_next_frontier(self, grid, turn):
        h, w = grid.shape
        rng = np.random.default_rng((hash(self.a_id) ^ int(turn)) & 0xFFFFFFFF)
        candidates = []
        for _ in range(40):
            y, x = int(rng.integers(0, h)), int(rng.integers(0, w))
            if grid[y, x] == 0:
                visits = int(self.exploration_map[y, x])
                dist = abs(y-self.pos[0]) + abs(x-self.pos[1])
                candidates.append(((y,x), visits, -dist))
        return min(candidates, key=lambda item: (item[1], item[2]))[0] if candidates else self.pos

    def tick(self):
        super().tick()
        remaining = []
        for pending in self.pending_keys:
            item = dict(pending)
            item["remaining"] -= 1
            if item["remaining"] <= 0:
                if item.get("real", False):
                    self.keys_identified += 1
            else:
                remaining.append(item)
        self.pending_keys = remaining
