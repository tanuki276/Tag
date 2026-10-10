import numpy as np

from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import ActionType, Intent, Priority


class Human(BaseActor):
    EXIT_COMMIT_STEPS = 4

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
        self.blocked_turns = 0
        self._last_decision_pos = tuple(pos)
        self.pending_keys = []
        self.keys_identified = 0

    def decide(self, view):
        self._update_blocked_state()

        if self.stun > 0:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT), action_type=ActionType.STAY)

        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=int(Priority.WAIT))

        finder = Pathfinder(grid)
        self._update_knowledge(view, grid)

        onis = [a for a in view.actors if a.is_oni and a.alive]
        nearby_humans = [a.pos for a in view.actors if not a.is_oni and a.alive]
        base_priority = int(self.config["entities"]["human"]["move_priority"])
        exit_open = bool(view.memory.get("exit_open"))

        if exit_open and self.known_exit is not None:
            exit_path = finder.get_path(self.pos, self.known_exit)
            exit_steps = max(0, len(exit_path) - 1)
            if exit_steps <= self.EXIT_COMMIT_STEPS:
                use_dash = bool(onis) and self.stamina >= self.dash_cost
                return Intent(
                    target_pos=self.known_exit,
                    priority=base_priority + 70,
                    action_type=ActionType.MOVE,
                    metadata={
                        "dash": use_dash,
                        "stamina_cost": self.dash_cost if use_dash else self.walk_cost,
                        "mode": "exit_commit",
                    },
                )

        if onis:
            self.target_node = None
            crowd_weight = 2.5 if self.blocked_turns >= 3 else 1.5
            target_pos = finder.get_safe_direction(
                self.pos,
                [o.pos for o in onis],
                distance=8,
                avoid_positions=nearby_humans,
                preferred_goal=self.known_exit if exit_open else None,
                crowd_weight=crowd_weight,
            )
            use_dash = self.stamina >= self.dash_cost
            return Intent(
                target_pos=target_pos,
                priority=base_priority + 30,
                action_type=ActionType.MOVE,
                metadata={
                    "dash": use_dash,
                    "stamina_cost": self.dash_cost if use_dash else self.walk_cost,
                    "mode": "flee",
                },
            )

        if exit_open and self.known_exit is not None:
            return Intent(
                target_pos=self.known_exit,
                priority=base_priority + 10,
                action_type=ActionType.MOVE,
                metadata={"stamina_cost": self.walk_cost, "mode": "exit"},
            )

        visible_keys = [e for e in view.elements if e.kind == "KEY"]
        if visible_keys:
            target = min(
                visible_keys,
                key=lambda e: abs(e.pos[0] - self.pos[0]) + abs(e.pos[1] - self.pos[1]),
            )
            return Intent(
                target_pos=target.pos,
                priority=base_priority + 5,
                action_type=ActionType.MOVE,
                metadata={"stamina_cost": self.walk_cost, "mode": "key"},
            )

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

        return Intent(
            target_pos=self.target_node,
            priority=base_priority,
            action_type=ActionType.MOVE,
            metadata={"stamina_cost": self.walk_cost, "mode": "explore"},
        )

    def _update_blocked_state(self):
        current = tuple(self.pos)
        if current == self._last_decision_pos:
            self.blocked_turns += 1
        else:
            self.blocked_turns = 0
        self._last_decision_pos = current

    def _update_knowledge(self, view, grid):
        if self.exploration_map is None:
            self.exploration_map = np.zeros_like(grid, dtype=np.int32)

        y, x = self.pos
        self.exploration_map[y, x] += 1

        if view.memory.get("exit_open") and view.memory.get("exit_pos") is not None:
            self.known_exit = tuple(view.memory["exit_pos"])

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
                dist = abs(y - self.pos[0]) + abs(x - self.pos[1])
                candidates.append(((y, x), visits, -dist))
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
