import numpy as np
from pkg.schema.models import LocalView

class InformationMediator:
    def __init__(self, config):
        self.config = config

    def get_local_views(self, state):
        alive_actors = [a for a in state.actor_data.values() if a.alive and not a.escaped]
        
        views = {}
        for actor in alive_actors:
            views[actor.a_id] = self._build_view(actor, state, alive_actors)
        return views

    def _build_view(self, actor, state, all_alive_actors):
        v_range = actor.vision_range
        if actor.stamina < 10:
            v_range = max(1, v_range // 2)

        visible_actors = [
            other.get_public_status() for other in all_alive_actors
            if other.a_id != actor.a_id and self._is_visible(actor.pos, other.pos, v_range, state.grid)
        ]
        
        visible_elements = [
            (pos, el) for pos, el in state.map_elements.items()
            if self._is_visible(actor.pos, pos, v_range, state.grid)
        ]

        mem = actor.memory.get_relevant(state.turn)
        mem["grid_map"] = state.grid

        return LocalView(
            pos=actor.pos, 
            actors=visible_actors, 
            elements=visible_elements, 
            memory=mem
        )

    def _is_visible(self, p1, p2, v_range, grid):
        if (abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])) > v_range:
            return False
        return not self._has_wall_between(p1, p2, grid)

    def _has_wall_between(self, p1, p2, grid):
        y0, x0 = p1
        y1, x1 = p2
        dy, dx = abs(y1 - y0), abs(x1 - x0)
        y, x = y0, x0
        n = 1 + dx + dy
        y_inc = 1 if y1 > y0 else -1
        x_inc = 1 if x1 > x0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2

        for _ in range(n):
            if grid[int(y), int(x)] == 1:
                if (int(y), int(x)) != p1 and (int(y), int(x)) != p2:
                    return True
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        return False

    def inject_learning(self, state, resolved_actions):
        alive_humans = [a for a in state.actor_data.values() if not a.is_oni and a.alive]
        
        for a_id, actor in state.actor_data.items():
            if actor.is_oni:
                for h in alive_humans:
                    if self._is_visible(actor.pos, h.pos, actor.vision_range, state.grid):
                        actor.memory.update_prediction(h.a_id, h.pos)

        self._process_oracle_transmission(state)

    def _process_oracle_transmission(self, state):
        active_oracles = [a for a in state.actor_data.values() if a.dream_mode > 0]
        if not active_oracles:
            return

        identified_keys = {
            pos: el for pos, el in state.map_elements.items() 
            if el.type.name == "KEY" and el.properties.get("identified")
        }

        if identified_keys:
            for h in state.actor_data.values():
                if not h.is_oni and h.alive:
                    h.memory.known_elements.update(identified_keys)
