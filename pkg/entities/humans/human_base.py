import random
import numpy as np
from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Intent

class Human(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = False
        self.is_human = True
        self.vision_range = config["entities"]["human"]["vision_range"]
        self.has_doll = config["entities"]["human"]["initial_dolls"] > 0
        self.stun = 0
        self.known_exit = None
        self.exploration_map = None
        self.target_node = None
        self.stuck_counter = 0

        self.stamina = 100
        self.max_stamina = 100
        self.dash_cost = 10
        self.walk_cost = 2
        self.recover_rate = 5

    def decide(self, view):
        if self.stun > 0:
            self._manage_stamina(0)
            return Intent(target_pos=self.pos, priority=0, metadata={"stamina": self.stamina})

        grid = view.memory.get("grid_map")
        if grid is None:
            return Intent(target_pos=self.pos, priority=0, metadata={})

        finder = Pathfinder(grid)
        self._update_knowledge(view, grid)

        onis = [a for a in view.actors if a.get("is_oni")]
        use_dash = len(onis) > 0 and self.stamina >= self.dash_cost
        priority_base = self.config["entities"]["human"]["move_priority"]

        if onis:
            self.target_node = None
            oni_positions = [tuple(o["pos"]) for o in onis]
            target_pos = finder.get_safe_direction(self.pos, oni_positions, distance=8)
            move_priority = priority_base + 10
        elif self.known_exit:
            path = finder.get_path(self.pos, self.known_exit)
            target_pos = tuple(path[1]) if len(path) > 1 else self.pos
            move_priority = priority_base + 2
        else:
            visible_keys = [pos for pos, el in view.elements if "KEY" in el.type.name]
            if visible_keys:
                target_key = min(visible_keys, key=lambda p: abs(p[0]-self.pos[0]) + abs(p[1]-self.pos[1]))
                path = finder.get_path(self.pos, target_key)
                target_pos = tuple(path[1]) if len(path) > 1 else self.pos
                move_priority = priority_base + 1
            else:
                if not self.target_node or tuple(self.pos) == tuple(self.target_node) or self.stuck_counter > 5:
                    self.target_node = self._select_next_frontier(grid)
                    self.stuck_counter = 0
                path = finder.get_path(self.pos, self.target_node)
                target_pos = tuple(path[1]) if len(path) > 1 else self.pos
                move_priority = priority_base

        if use_dash:
            path_dash = finder.get_path(self.pos, target_pos)
            if len(path_dash) > 2:
                final_pos = tuple(path_dash[2])
            elif len(path_dash) > 1:
                final_pos = tuple(path_dash[1])
            else:
                final_pos = self.pos
            self._manage_stamina(self.dash_cost)
            move_priority += 5
        else:
            final_pos = target_pos
            if tuple(final_pos) != tuple(self.pos):
                self._manage_stamina(self.walk_cost)
            else:
                self._manage_stamina(0)

        if tuple(final_pos) == tuple(self.prev_pos) and tuple(final_pos) != tuple(self.pos):
            self.stuck_counter += 1

        return Intent(
            target_pos=tuple(final_pos), 
            priority=move_priority,
            metadata={"dash": use_dash, "stamina": self.stamina, "ignore_walls": False}
        )

    def _manage_stamina(self, cost):
        if cost > 0:
            self.stamina = max(0, self.stamina - cost)
        else:
            self.stamina = min(self.max_stamina, self.stamina + self.recover_rate)

    def _update_knowledge(self, view, grid):
        if self.exploration_map is None:
            self.exploration_map = np.zeros_like(grid)
        y, x = self.pos
        self.exploration_map[y, x] += 1
        for pos, el in view.elements:
            if el.type.name == "EXIT":
                self.known_exit = tuple(pos)

    def _select_next_frontier(self, grid):
        h, w = grid.shape
        candidates = []
        for _ in range(15):
            ty, tx = random.randint(0, h-1), random.randint(0, w-1)
            if grid[ty, tx] == 0:
                score = self.exploration_map[ty, tx]
                candidates.append(((ty, tx), score))
        if not candidates:
            return self.pos
        return min(candidates, key=lambda x: x[1])[0]
