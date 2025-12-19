import numpy as np
from pkg.entities.actor import BaseActor
from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Intent

class Oni(BaseActor):
    shared_targets = {}
    shared_onis = {}
    _dijkstra_maps = {}
    _next_intent_map = {}
    _common_pathfinder = None
    _last_sync_turn = -1

    @classmethod
    def reset_shared_memory(cls):
        cls.shared_targets.clear()
        cls.shared_onis.clear()
        cls._dijkstra_maps.clear()
        cls._next_intent_map.clear()
        cls._common_pathfinder = None
        cls._last_sync_turn = -1

    def __init__(self, a_id, pos, config, role="CHASER"):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.role = role
        self.target_id = None

    def decide(self, view):
        grid = view.memory.get("grid_map")
        turn = view.memory.get("current_turn", 0)
        if grid is None: return Intent(target_pos=self.pos, priority=0)

        self._global_sync(view, grid, turn)
        self._select_best_target(turn)

        if self.target_id and self.target_id in Oni.shared_targets:
            info = Oni.shared_targets[self.target_id]
            target_pos = self._calculate_predatory_pos(info, grid)
            dist = self._l1_dist(self.pos, info["pos"])
            # 距離に応じた適度な優先度。少し「揺らぎ」を持たせる
            priority = 90 if dist < 3 else 70
        else:
            target_pos = self._get_strategic_patrol(grid, turn)
            priority = 20

        return self._hierarchical_move(target_pos, grid, priority)

    def _global_sync(self, view, grid, turn):
        if Oni._last_sync_turn != turn:
            Oni._common_pathfinder = Pathfinder(grid)
            Oni._last_sync_turn = turn
            Oni._dijkstra_maps.clear()
            Oni._next_intent_map.clear()
            
            Oni.shared_onis = {a["a_id"]: {"pos": tuple(map(int, a["pos"])), "role": a.get("role", "CHASER")} 
                               for a in view.actors if a.get("is_oni")}

            for a in view.actors:
                if not a.get("is_oni") and a.get("alive"):
                    tid, n_pos = a["a_id"], tuple(map(int, a["pos"]))
                    old = Oni.shared_targets.get(tid, {"pos": n_pos})
                    # 1. 速度予測のリミッター（飛びすぎ防止）
                    raw_vel = np.array([n_pos[0] - old["pos"][0], n_pos[1] - old["pos"][1]])
                    lim_vel = np.clip(raw_vel, -1, 1) * 2 
                    pred_pos = (int(n_pos[0] + lim_vel[0]), int(n_pos[1] + lim_vel[1]))
                    eval_pos = pred_pos if self._is_valid(pred_pos, grid) else n_pos
                    
                    Oni.shared_targets[tid] = {"pos": n_pos, "pred_pos": eval_pos, "turn": turn}
                    Oni._dijkstra_maps[tid] = Oni._common_pathfinder.generate_dijkstra_map(eval_pos)

    def _calculate_predatory_pos(self, info, grid):
        t_pos = np.array(info["pos"])
        pred_pos = np.array(info["pred_pos"])
        d_map = Oni._dijkstra_maps[self.target_id]

        if self.role == "CHASER":
            return tuple(t_pos.astype(int))

        if self.role == "BLOCKER":
            # 2. 到着後は周辺を「うろうろ」して網を広げる
            base_choke = self._find_escape_route_block(pred_pos, d_map, grid)
            if self._l1_dist(self.pos, base_choke) <= 1:
                return self._get_jitter_pos(base_choke, grid)
            return base_choke

        if self.role == "AMBUSHER":
            return self._find_active_ambush(pred_pos, grid)

    def _find_escape_route_block(self, pred_pos, d_map, grid):
        best_choke, min_score = tuple(pred_pos), float('inf')
        for r in range(1, 6):
            for dx, dy in [(r,0),(-r,0),(0,r),(0,-r)]:
                p = (int(pred_pos[0]+dx), int(pred_pos[1]+dy))
                if self._is_valid(p, grid):
                    conn = sum(1 for m in [(0,1),(0,-1),(1,0),(-1,0)] if self._is_valid((p[0]+m[0], p[1]+m[1]), grid))
                    score = d_map[p] + (0 if conn >= 3 else 15)
                    if score < min_score:
                        min_score, best_choke = score, p
        return best_choke

    def _get_jitter_pos(self, center, grid):
        """目的地の周辺1マスでランダムに揺らす（封鎖の厚みを出す）"""
        rng = np.random.default_rng()
        candidates = [(center[0]+dx, center[1]+dy) for dx, dy in [(0,0),(0,1),(0,-1),(1,0),(-1,0)]]
        valid = [c for c in candidates if self._is_valid(c, grid)]
        return tuple(rng.choice(valid)) if valid else center

    def _hierarchical_move(self, target_pos, grid, priority):
        temp_grid = grid.copy()
        for pos, oid in Oni._next_intent_map.items():
            if oid < self.a_id: temp_grid[pos] = 1
        
        try:
            nxt = Pathfinder(temp_grid).get_next_step(self.pos, target_pos)
            if nxt is None: raise ValueError
        except:
            # 3. 譲り合いのデッドロック解消（低確率でランダム移動）
            rng = np.random.default_rng()
            if rng.random() < 0.2:
                moves = [(self.pos[0]+dx, self.pos[1]+dy) for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]]
                valid = [m for m in moves if self._is_valid(m, grid) and m not in Oni._next_intent_map]
                nxt = rng.choice(valid) if valid else self.pos
            else:
                nxt = self.pos

        nxt_tuple = tuple(map(int, nxt))
        Oni._next_intent_map[nxt_tuple] = self.a_id
        return Intent(target_pos=nxt_tuple, priority=priority)

    def _is_valid(self, p, grid):
        return 0 <= p[0] < grid.shape[0] and 0 <= p[1] < grid.shape[1] and grid[p] == 0

    def _l1_dist(self, p1, p2):
        return abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])

    def _select_best_target(self, turn):
        valid_tids = [tid for tid, info in Oni.shared_targets.items() if turn - info["turn"] < 5]
        if not valid_tids: return
        self.target_id = min(valid_tids, key=lambda tid: self._l1_dist(self.pos, Oni.shared_targets[tid]["pos"]))

    def _find_active_ambush(self, pred_pos, grid):
        best_trap, min_conn = tuple(pred_pos.astype(int)), 5
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                p = (int(pred_pos[0]+dx), int(pred_pos[1]+dy))
                if self._is_valid(p, grid):
                    conn = sum(1 for m in [(0,1),(0,-1),(1,0),(-1,0)] if self._is_valid((p[0]+m[0], p[1]+m[1]), grid))
                    if conn < min_conn:
                        min_conn, best_trap = conn, p
        return best_trap

    def _get_strategic_patrol(self, grid, turn):
        w, h = grid.shape
        rng = np.random.default_rng(hash(self.a_id) + turn)
        return (rng.integers(0, w), rng.integers(0, h))
