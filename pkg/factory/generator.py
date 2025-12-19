import numpy as np
import random
from pkg.engine.map.manager import MapManager
from pkg.engine.map.mapelement import ElementType
from pkg.engine.state import WorldState
from pkg.entities.humans.oracle import Oracle
from pkg.entities.humans.human_base import Human
from pkg.entities.onis.oni_base import Oni

class WorldGenerator:
    def __init__(self, seed=None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def build_initial_state(self, config):
        map_mgr = self._generate_map(config)
        actors = self._spawn_entities(map_mgr, config)
        return WorldState(map_mgr.grid, actors, {"items": map_mgr.elements}, config)

    def _generate_map(self, config):
        mgr = MapManager(config)
        size = config["world"]["grid_size"]
        density = config["world"]["wall_density"]
        grid = (np.random.rand(size, size) < density).astype(int)

        for _ in range(config.get("generation", {}).get("smooth_iterations", 2)):
            new_grid = grid.copy()
            for x in range(1, size-1):
                for y in range(1, size-1):
                    neighbors = np.sum(grid[x-1:x+2, y-1:y+2]) - grid[x, y]
                    if neighbors > 4: new_grid[x, y] = 1
                    elif neighbors < 3: new_grid[x, y] = 0
            grid = new_grid

        mgr.grid = grid
        empty_cells = [(x, y) for x in range(size) for y in range(size) if mgr.grid[x, y] == 0]
        random.shuffle(empty_cells)

        exit_pos = empty_cells.pop()
        mgr.add_element(exit_pos, ElementType.EXIT)
        config["world"]["exit_pos"] = exit_pos

        total_keys = config["game_rules"]["total_keys_spawned"]
        for _ in range(total_keys):
            if not empty_cells: break
            k_pos = empty_cells.pop()
            is_real = random.random() > config["game_rules"]["fake_key_ratio"]
            mgr.add_element(k_pos, ElementType.KEY, {"is_real": is_real, "identified": False})

        return mgr

    def _spawn_entities(self, mgr, config):
        actors = {}
        size = config["world"]["grid_size"]
        empty_cells = [(x, y) for x in range(size) for y in range(size) 
                       if mgr.grid[x, y] == 0 and (x, y) not in mgr.elements]

        spawn_mode = config.get("spawn_logic", {}).get("mode", "CLUSTER")
        if spawn_mode == "CLUSTER":
            center = random.choice(empty_cells)
            h_positions = self._get_cluster_positions(center, config["entities"]["human"]["count"], empty_cells)
        else:
            random.shuffle(empty_cells)
            h_positions = [empty_cells.pop() for _ in range(config["entities"]["human"]["count"])]

        for i, pos in enumerate(h_positions):
            a_id = f"H{i}"
            actors[a_id] = Oracle(a_id, pos, config) if i == 0 else Human(a_id, pos, config)

        o_count = config["entities"]["oni"]["count"]
        for i in range(o_count):
            if not empty_cells: break
            o_pos = max(empty_cells, key=lambda p: min([abs(p[0]-h.pos[0]) + abs(p[1]-h.pos[1]) for h in actors.values()]))
            empty_cells.remove(o_pos)
            a_id = f"O{i}"
            actors[a_id] = Oni(a_id, pos=o_pos, config=config)

        return actors

    def _get_cluster_positions(self, center, count, empty_cells):
        cluster = []
        sorted_cells = sorted(empty_cells, key=lambda p: abs(p[0]-center[0]) + abs(p[1]-center[1]))
        for _ in range(count):
            if sorted_cells:
                pos = sorted_cells.pop(0)
                cluster.append(pos)
                if pos in empty_cells: empty_cells.remove(pos)
        return cluster
