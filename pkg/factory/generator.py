import numpy as np
import random
from pkg.engine.map.manager import MapManager
from pkg.engine.map.mapelement import ElementType
from pkg.engine.state import WorldState
from pkg.entities.humans.oracle import Oracle
from pkg.entities.actor import Human, Oni

class WorldGenerator:
    def __init__(self, seed: int = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def build_initial_state(self, config: dict) -> WorldState:
        map_mgr = self._generate_map(config)
        actors = self._spawn_entities(map_mgr, config)
        return WorldState(config, map_mgr.grid, actors, map_mgr.elements)

    def _generate_map(self, config: dict) -> MapManager:
        mgr = MapManager(config)
        size = config["world"]["grid_size"]
        density = config["world"]["wall_density"]
        
        # Cellular Automata Simple Implementation
        mgr.grid = (np.random.rand(size, size) < density).astype(int)
        
        candidates = [(x, y) for x in range(size) for y in range(size) if mgr.grid[x, y] == 0]
        random.shuffle(candidates)
        
        exit_pos = candidates.pop()
        mgr.add_element(exit_pos, ElementType.EXIT)
        
        for _ in range(config["game_rules"]["total_keys_spawned"]):
            if not candidates: break
            k_pos = candidates.pop()
            is_real = random.random() > config["game_rules"]["fake_key_ratio"]
            mgr.add_element(k_pos, ElementType.KEY, {"is_real": is_real})
            
        return mgr

    def _spawn_entities(self, mgr: MapManager, config: dict) -> dict:
        actors = {}
        size = config["world"]["grid_size"]
        empty_cells = [(x, y) for x in range(size) for y in range(size) if mgr.grid[x, y] == 0 and (x, y) not in mgr.elements]
        
        # Human Cluster Spawn
        center = random.choice(empty_cells)
        h_count = config["entities"]["human"]["count"]
        
        for i in range(h_count):
            pos = self._get_nearby_pos(center, mgr, empty_cells)
            a_id = f"H{i}"
            if i == 0:
                actors[a_id] = Oracle(a_id, pos, config)
            else:
                actors[a_id] = Human(a_id, pos, config)

        # Oni Distant Spawn
        o_count = config["entities"]["oni"]["count"]
        for i in range(o_count):
            pos = max(empty_cells, key=lambda p: min([abs(p[0]-h.pos[0])+abs(p[1]-h.pos[1]) for h in actors.values()]))
            empty_cells.remove(pos)
            a_id = f"O{i}"
            actors[a_id] = Oni(a_id, pos, config)
            
        return actors

    def _get_nearby_pos(self, center, mgr, empty_cells):
        for r in range(5):
            near = [p for p in empty_cells if abs(p[0]-center[0]) + abs(p[1]-center[1]) <= r]
            if near:
                p = random.choice(near)
                empty_cells.remove(p)
                return p
        return random.choice(empty_cells)
