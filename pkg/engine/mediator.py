import numpy as np
from pkg.schema.models import LocalView

class InformationMediator:
    def __init__(self, config: dict):
        self.config = config

    def get_local_views(self, state: 'WorldState') -> dict:
        views = {}
        for a_id, actor in state.actor_data.items():
            if not actor.alive or actor.escaped:
                continue
            
            views[a_id] = self._generate_view(a_id, actor, state)
        return views

    def _generate_view(self, a_id: str, actor: 'BaseActor', state: 'WorldState') -> LocalView:
        v_range = actor.vision_range
        pos = actor.pos
        
        visible_actors = []
        for other_id, other in state.actor_data.items():
            if a_id == other_id or not other.alive:
                continue
            if self._is_in_range(pos, other.pos, v_range):
                if not self._is_obstructed(pos, other.pos, state.grid):
                    visible_actors.append(other.get_public_status())

        visible_elements = []
        for e_pos, element in state.map_elements.items():
            if self._is_in_range(pos, e_pos, v_range):
                if not self._is_obstructed(pos, e_pos, state.grid):
                    visible_elements.append((e_pos, element))

        return LocalView(
            pos=pos,
            actors=visible_actors,
            elements=visible_elements,
            memory=actor.memory.get_relevant(state.turn)
        )

    def _is_in_range(self, p1: tuple, p2: tuple, v_range: int) -> bool:
        return (abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])) <= v_range

    def _is_obstructed(self, p1: tuple, p2: tuple, grid: np.ndarray) -> bool:
        x0, y0 = p1
        x1, y1 = p2
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2

        for _ in range(n):
            if grid[x, y] == 1: # Wall
                if (x, y) != p1 and (x, y) != p2:
                    return True
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
        return False

    def inject_learning(self, state: 'WorldState', analysis_data: dict):
        for a_id, actor in state.actor_data.items():
            if actor.is_oni:
                actor.memory.update_prediction_model(analysis_data)
