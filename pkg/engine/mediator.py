import numpy as np
from pkg.schema.models import LocalView

class InformationMediator:
    def __init__(self, config):
        self.config = config

    def get_local_views(self, state):
        return {
            a_id: self._build_view(actor, state)
            for a_id, actor in state.actor_data.items()
            if actor.alive and not actor.escaped
        }

    def _build_view(self, actor, state):
        v_range = actor.vision_range
        visible_actors = [
            other.get_public_status() for a_id, other in state.actor_data.items()
            if a_id != actor.a_id and other.alive and self._is_visible(actor.pos, other.pos, v_range, state.grid)
        ]
        visible_elements = [
            (pos, el) for pos, el in state.map_elements.items()
            if self._is_visible(actor.pos, pos, v_range, state.grid)
        ]
        return LocalView(pos=actor.pos, actors=visible_actors, elements=visible_elements, memory=actor.memory.get_relevant(state.turn))

    def _is_visible(self, p1, p2, v_range, grid):
        if (abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])) > v_range: return False
        return not self._has_wall_between(p1, p2, grid)

    def _has_wall_between(self, p1, p2, grid):
        # Bresenham-like line algorithm for LOS
        x0, y0 = p1
        x1, y1 = p2
        dx, dy = abs(x1-x0), abs(y1-y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2
        for _ in range(n):
            if grid[x, y] == 1 and (x, y) != p1 and (x, y) != p2: return True
            if error > 0: x += x_inc; error -= dy
            else: y += y_inc; error += dx
        return False

    def inject_learning(self, state, resolved_actions):
        # Update Oni memory based on human movement patterns
        pass
