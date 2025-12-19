import heapq
import numpy as np
from collections import defaultdict

class Pathfinder:
    def __init__(self, grid):
        self.grid = grid
        self.height, self.width = grid.shape

    def get_next_step(self, start, goal):
        s, g = tuple(start), tuple(goal)
        if s == g: return s
        path = self._astar(s, g)
        return path[1] if len(path) > 1 else s

    def has_los(self, start, end):
        y0, x0 = start
        y1, x1 = end
        dy, dx = abs(y1 - y0), abs(x1 - x0)
        sy = 1 if y0 < y1 else -1
        sx = 1 if x0 < x1 else -1
        err = dx - dy
        curr_y, curr_x = y0, x0
        while (curr_y, curr_x) != (y1, x1):
            if not (0 <= curr_y < self.height and 0 <= curr_x < self.width):
                return False
            if self.grid[curr_y, curr_x] == 1:
                return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                curr_x += sx
            if e2 < dx:
                err += dx
                curr_y += sy
        return True

    def _astar(self, start, goal):
        if not (0 <= goal[0] < self.height and 0 <= goal[1] < self.width) or self.grid[goal] == 1:
            return [start]
        oheap = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        close_set = set()
        c1, c2 = 1.0, 1.414
        while oheap:
            _, current = heapq.heappop(oheap)
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                return [start] + path[::-1]
            if current in close_set: continue
            close_set.add(current)
            for di, dj in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                ni, nj = current[0] + di, current[1] + dj
                neighbor = (ni, nj)
                if not (0 <= ni < self.height and 0 <= nj < self.width) or self.grid[neighbor] == 1:
                    continue
                if di != 0 and dj != 0:
                    if self.grid[current[0] + di, current[1]] == 1 or self.grid[current[0], current[1] + dj] == 1:
                        continue
                    cost = c2
                else:
                    cost = c1
                tg = g_score[current] + cost
                if tg < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tg
                    f = tg + self._dist(neighbor, goal)
                    heapq.heappush(oheap, (f, neighbor))
        return [start]

    def _dist(self, a, b):
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        return dx + dy + (1.414 - 2.0) * (dx if dx < dy else dy)

class ActionResolver:
    def __init__(self, config):
        self.config = config
        self.pathfinder = None

    def resolve(self, intents, state):
        if self.pathfinder is None:
            self.pathfinder = Pathfinder(state.grid)
        sorted_ids = sorted(intents.keys(), key=lambda x: (intents[x].priority, state.actor_data[x].is_oni), reverse=True)
        status_updates = defaultdict(dict)
        self._handle_ongoing_buffs(state, status_updates)
        skill_executed = self._prepare_skills(intents, state, status_updates)
        planned_paths = {}
        final_positions = self._resolve_movement_collision(sorted_ids, intents, state, status_updates, planned_paths)
        self._resolve_combat_refined(final_positions, state, planned_paths, status_updates)
        self._resolve_items(final_positions, state, status_updates)
        self._finalize_actions(state, status_updates, skill_executed)
        from pkg.schema.models import Action
        return {a_id: Action(target_pos=pos, status_update=status_updates[a_id]) for a_id, pos in final_positions.items()}

    def _handle_ongoing_buffs(self, state, status_updates):
        for a_id, actor in state.actor_data.items():
            d = getattr(actor, 'asclepius_duration', 0)
            if d > 0:
                new_d = d - 1
                status_updates[a_id]['asclepius_duration'] = new_d
                if new_d == 0:
                    status_updates[a_id].update({'stamina_rate': 1.0, 'asclepius_active': False})

    def _resolve_movement_collision(self, sorted_ids, intents, state, status_updates, planned_paths):
        final_positions = {}
        occupied = {tuple(a.pos) for a in state.actor_data.values() if not a.alive or a.escaped}
        for a_id in sorted_ids:
            actor = state.actor_data[a_id]
            target = tuple(intents[a_id].target_pos)
            speed = 2 if status_updates[a_id].get("asclepius_active") or getattr(actor, 'asclepius_active', False) else 1
            full_path = self.pathfinder._astar(tuple(actor.pos), target) if tuple(actor.pos) != target else [tuple(actor.pos)]
            path = (full_path or [tuple(actor.pos)])[:speed + 1]
            while len(path) > 1 and (path[-1] in occupied or path[-1] in final_positions.values()):
                path.pop()
            final_positions[a_id] = list(path[-1])
            planned_paths[a_id] = path
        return final_positions

    def _resolve_combat_refined(self, final_positions, state, planned_paths, status_updates):
        onis = [i for i, a in state.actor_data.items() if a.is_oni]
        humans = [i for i, a in state.actor_data.items() if not a.is_oni and a.alive]
        for h_id in humans:
            h_actor = state.actor_data[h_id]
            if getattr(h_actor, 'invincible', False): continue
            h_p = planned_paths[h_id]
            for o_id in onis:
                o_p = planned_paths[o_id]
                collision = (final_positions[h_id] == final_positions[o_id])
                if not collision and len(h_p) > 1 and len(o_p) > 1:
                    if h_p[0] == o_p[1] and h_p[1] == o_p[0]: collision = True
                if collision:
                    if self.pathfinder.has_los(h_p[0], o_p[0]):
                        if getattr(h_actor, 'has_doll', False):
                            status_updates[h_id]['has_doll'] = False
                            final_positions[h_id] = list(h_p[0])
                        else:
                            status_updates[h_id]['alive'] = False
                            final_positions[h_id] = list(h_p[0])
                    break

    def _prepare_skills(self, intents, state, status_updates):
        executed = set()
        for a_id, intent in intents.items():
            if intent.action == "ASCLEPIUS":
                actor = state.actor_data[a_id]
                if getattr(actor, 'mp_charge', 0) >= 1000:
                    executed.add(a_id)
                    for t_id, t_a in state.actor_data.items():
                        if not t_a.is_oni and self.pathfinder.has_los(actor.pos, t_a.pos):
                            if (abs(actor.pos[0]-t_a.pos[0])+abs(actor.pos[1]-t_a.pos[1])) <= 10:
                                status_updates[t_id].update({"asclepius_active": True, "asclepius_duration": 5, "stamina_rate": 0.3})
        return executed

    def _finalize_actions(self, state, status_updates, skill_executed):
        for a_id in skill_executed:
            if status_updates[a_id].get('alive', state.actor_data[a_id].alive):
                state.actor_data[a_id].mp_charge -= 1000

    def _resolve_items(self, final_positions, state, status_updates):
        for a_id, pos in final_positions.items():
            if not status_updates[a_id].get('alive', state.actor_data[a_id].alive): continue
            p = tuple(pos)
            item = state.grid_items.get(p)
            if item:
                if item.type == "DOLL":
                    status_updates[a_id]['has_doll'] = True
                    state.grid_items.pop(p)
                elif item.type == "MP_POTION":
                    state.actor_data[a_id].mp_charge = min(state.actor_data[a_id].mp_charge + 500, 1000)
                    state.grid_items.pop(p)
