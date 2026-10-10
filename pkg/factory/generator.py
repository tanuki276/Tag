from collections import deque

import numpy as np

from pkg.engine.state import WorldState
from pkg.entities.humans.human_base import Human
from pkg.entities.humans.oracle import Oracle
from pkg.entities.onis.oni_base import Oni
from pkg.schema.models import Element


class WorldGenerator:
    def __init__(self, seed=None, generation_cfg=None):
        self.seed = seed
        self.generation_cfg = generation_cfg or {}
        self.rng = np.random.default_rng(seed)

    def build_initial_state(self, config):
        size = int(config["world"]["grid_size"])
        wall_density = float(config["world"].get("wall_density", 0.2))
        grid, walkable = self._build_connected_grid(size, wall_density)

        human_count = int(config["entities"]["human"]["count"])
        oracle_count = min(human_count, int(config["entities"]["human"].get("oracle_count", 1)))
        oni_count = int(config["entities"]["oni"]["count"])
        human_cells, oni_cells, exit_pos, item_cells = self._allocate_positions(walkable, human_count, oni_count)

        actors = {}
        normal_humans = human_count - oracle_count
        for idx in range(normal_humans):
            actors[f"H{idx:02d}"] = Human(f"H{idx:02d}", human_cells[idx], config)
        for idx in range(oracle_count):
            cell = human_cells[normal_humans + idx]
            actors[f"ORACLE{idx:02d}"] = Oracle(f"ORACLE{idx:02d}", cell, config)

        roles = ("CHASER", "BLOCKER", "AMBUSHER")
        for idx in range(oni_count):
            actors[f"O{idx:02d}"] = Oni(f"O{idx:02d}", oni_cells[idx], config, role=roles[idx % len(roles)])

        items = {exit_pos: Element(pos=exit_pos, kind="EXIT")}
        self._place_keys(items, item_cells, config)
        extras = config.get("items", {})
        remaining = [p for p in item_cells if p not in items]
        self.rng.shuffle(remaining)
        for _ in range(min(int(extras.get("dolls_spawned", 3)), len(remaining))):
            pos = remaining.pop()
            items[pos] = Element(pos=pos, kind="DOLL")
        for _ in range(min(int(extras.get("mp_potions_spawned", 3)), len(remaining))):
            pos = remaining.pop()
            items[pos] = Element(pos=pos, kind="MP_POTION")

        return WorldState(grid=grid, actor_data=actors, map_elements=items, config=config, exit_pos=exit_pos)

    def _build_connected_grid(self, size, wall_density):
        for _ in range(30):
            grid = (self.rng.random((size, size)) < wall_density).astype(np.int8)
            grid[0, :] = grid[-1, :] = 1
            grid[:, 0] = grid[:, -1] = 1
            component = self._largest_component(grid)
            if len(component) >= max(40, size * size // 2):
                return grid, component
        grid = np.zeros((size, size), dtype=np.int8)
        grid[0, :] = grid[-1, :] = 1
        grid[:, 0] = grid[:, -1] = 1
        return grid, self._largest_component(grid)

    def _largest_component(self, grid):
        visited, best = set(), []
        h, w = grid.shape
        for y in range(h):
            for x in range(w):
                start = (y, x)
                if grid[start] == 1 or start in visited:
                    continue
                component = []
                queue = deque([start])
                visited.add(start)
                while queue:
                    cur = queue.popleft()
                    component.append(cur)
                    for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
                        nxt = (cur[0]+dy, cur[1]+dx)
                        if 0 <= nxt[0] < h and 0 <= nxt[1] < w and grid[nxt] == 0 and nxt not in visited:
                            visited.add(nxt)
                            queue.append(nxt)
                if len(component) > len(best):
                    best = component
        return best

    def _allocate_positions(self, walkable, human_count, oni_count):
        cells = list(walkable)
        self.rng.shuffle(cells)
        anchor = cells[0]
        human_cells = sorted(cells, key=lambda p: abs(p[0]-anchor[0]) + abs(p[1]-anchor[1]))[:human_count]
        used = set(human_cells)
        min_dist = int(self.generation_cfg.get("spawn_logic", {}).get("min_dist_human_to_oni", 12))
        oni_candidates = [p for p in cells if p not in used and min(abs(p[0]-h[0])+abs(p[1]-h[1]) for h in human_cells) >= min_dist]
        if len(oni_candidates) < oni_count:
            oni_candidates = [p for p in cells if p not in used]
            oni_candidates.sort(key=lambda p: min(abs(p[0]-h[0])+abs(p[1]-h[1]) for h in human_cells), reverse=True)
        oni_cells = oni_candidates[:oni_count]
        used.update(oni_cells)
        exit_candidates = [p for p in cells if p not in used]
        exit_pos = max(exit_candidates, key=lambda p: min(abs(p[0]-h[0])+abs(p[1]-h[1]) for h in human_cells))
        used.add(exit_pos)
        return human_cells, oni_cells, exit_pos, [p for p in cells if p not in used]

    def _place_keys(self, items, item_cells, config):
        rules = config["game_rules"]
        total = min(int(rules.get("total_keys_spawned", 16)), len(item_cells))
        fake_ratio = float(rules.get("fake_key_ratio", 0.5))
        needed = int(rules.get("num_keys_needed", 5))
        available = list(item_cells)
        self.rng.shuffle(available)
        real_count = min(total, max(needed, int(round(total * (1.0 - fake_ratio)))))
        flags = [True] * real_count + [False] * (total - real_count)
        self.rng.shuffle(flags)
        for pos, is_real in zip(available[:total], flags):
            items[pos] = Element(pos=pos, kind="KEY", properties={"real": bool(is_real)})
