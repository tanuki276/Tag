from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import LocalView


class InformationMediator:
    def __init__(self, config):
        self.config = config

    def get_local_views(self, state):
        active = [a for a in state.actor_data.values() if a.alive and not a.escaped]
        views = {actor.a_id: self._build_view(actor, state, active) for actor in active}
        self._share_oni_sightings(views, state)
        return views

    def _build_view(self, actor, state, active):
        vision = getattr(actor, "vision_range", 5)
        if not actor.is_oni and getattr(actor, "stamina", 100) < 10:
            vision = max(1, vision // 2)

        oracle = getattr(actor, "job", None) == "ORACLE"
        visible_actors = []
        for other in active:
            if other.a_id == actor.a_id:
                continue
            if self._is_visible(actor.pos, other.pos, vision, state.grid, ignore_walls=oracle):
                status = other.get_public_status()
                visible_actors.append(status)
                actor.memory.update_seen_actor(other.a_id, status, state.turn)
                if actor.is_oni and not other.is_oni:
                    actor.memory.update_prediction(other.a_id, other.pos)

        visible_elements = []
        for pos, element in state.grid_items.items():
            if self._is_visible(actor.pos, pos, vision, state.grid):
                visible_elements.append(element)
                actor.memory.record_element(pos, element)

        memory = actor.memory.get_relevant(state.turn)
        memory["grid_map"] = state.grid
        memory["exit_open"] = state.exit_open
        memory["exit_pos"] = state.exit_pos

        return LocalView(
            pos=actor.pos,
            actors=visible_actors,
            elements=visible_elements,
            memory=memory,
        )

    def _share_oni_sightings(self, views, state):
        shared = {}
        for a_id, view in views.items():
            if not state.actor_data[a_id].is_oni:
                continue
            for status in view.actors:
                if not status.is_oni:
                    shared[status.a_id] = status

        if not shared:
            return

        for a_id, view in views.items():
            actor = state.actor_data[a_id]
            if not actor.is_oni:
                continue
            present = {status.a_id for status in view.actors}
            for target_id, status in shared.items():
                if target_id not in present:
                    actor.memory.update_seen_actor(target_id, status, state.turn)
                    actor.memory.update_prediction(target_id, status.pos)
                    view.actors.append(status)
            view.memory = actor.memory.get_relevant(state.turn)
            view.memory["grid_map"] = state.grid
            view.memory["exit_open"] = state.exit_open
            view.memory["exit_pos"] = state.exit_pos

    def _is_visible(self, p1, p2, vision, grid, ignore_walls=False):
        p1, p2 = tuple(map(int, p1)), tuple(map(int, p2))
        if abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) > vision:
            return False
        if ignore_walls:
            return True
        return Pathfinder(grid).has_los(p1, p2)

    def inject_learning(self, state, resolved_actions):
        return None
