import numpy as np
from collections import defaultdict
from pkg.schema.models import Intent, Priority, ActionType
from pkg.engine.pathfinder import Pathfinder

class ActionResolver:
    def __init__(self, config):
        self.config = config
        self.pathfinder = None

    def resolve(self, intents, state):
        if self.pathfinder is None:
            self.pathfinder = Pathfinder(state.grid)

        sorted_ids = sorted(
            intents.keys(),
            key=lambda x: (intents[x].priority, state.actor_data[x].is_oni),
            reverse=True
        )

        status_updates = defaultdict(dict)

        self._handle_ongoing_buffs(state, status_updates)
        skill_executed = self._prepare_skills(intents, state, status_updates)

        planned_paths = {}
        final_positions = self._resolve_movement_collision(
            sorted_ids, intents, state, status_updates, planned_paths
        )

        self._resolve_combat_refined(final_positions, state, planned_paths, status_updates)
        self._resolve_items(final_positions, state, status_updates)
        self._finalize_actions(state, status_updates, skill_executed)

        return {
            a_id: Intent(
                target_pos=pos,
                priority=intents[a_id].priority,
                action_type=intents[a_id].action_type,
                metadata=status_updates[a_id]
            )
            for a_id, pos in final_positions.items()
        }

    def _handle_ongoing_buffs(self, state, status_updates):
        for a_id, actor in state.actor_data.items():
            duration = getattr(actor, 'asclepius_duration', 0)
            if duration > 0:
                new_duration = duration - 1
                status_updates[a_id]['asclepius_duration'] = new_duration
                if new_duration == 0:
                    status_updates[a_id]['stamina_rate'] = 1.0
                    status_updates[a_id]['asclepius_active'] = False

    def _resolve_movement_collision(self, sorted_ids, intents, state, status_updates, planned_paths):
        final_positions = {}
        occupied = {tuple(a.pos) for a in state.actor_data.values() if a.alive and not getattr(a, 'escaped', False)}

        for a_id in sorted_ids:
            actor = state.actor_data[a_id]
            if not actor.alive or getattr(actor, 'escaped', False):
                continue

            current_pos = tuple(actor.pos)
            if current_pos in occupied:
                occupied.remove(current_pos)

            target_pos = tuple(intents[a_id].target_pos)
            speed = 2 if status_updates[a_id].get("asclepius_active") or \
                        getattr(actor, 'asclepius_active', False) else 1

            if current_pos == target_pos:
                path = [current_pos]
            else:
                full_path = self.pathfinder._astar(current_pos, target_pos)
                path = (full_path or [current_pos])[:speed + 1]

            while len(path) > 1 and path[-1] in occupied:
                path.pop()

            final_pos = path[-1]
            final_positions[a_id] = list(final_pos)
            planned_paths[a_id] = path
            occupied.add(final_pos)

        return final_positions

    def _resolve_combat_refined(self, final_positions, state, planned_paths, status_updates):
        onis = [a_id for a_id, a in state.actor_data.items() if a.is_oni]
        humans = [a_id for a_id, a in state.actor_data.items() if not a.is_oni and a.alive]

        for h_id in humans:
            h_actor = state.actor_data[h_id]
            if getattr(h_actor, 'invincible', False) or status_updates[h_id].get('alive') is False:
                continue

            h_path = [tuple(p) for p in planned_paths.get(h_id, [])]
            for o_id in onis:
                o_path = [tuple(p) for p in planned_paths.get(o_id, [])]
                if not h_path or not o_path: 
                    continue

                collision = False
                if h_path[-1] == o_path[-1]:
                    collision = True
                elif len(set(h_path) & set(o_path)) > 1:
                    collision = True

                if collision:
                    if getattr(h_actor, 'has_doll', False):
                        status_updates[h_id]['has_doll'] = False
                        final_positions[h_id] = list(h_path[0])
                    else:
                        status_updates[h_id]['alive'] = False
                        final_positions[h_id] = list(h_path[0])
                    break

    def _prepare_skills(self, intents, state, status_updates):
        executed = set()
        for a_id, intent in intents.items():
            if getattr(intent, 'action_type', None) == ActionType.SKILL and getattr(intent, 'metadata', {}).get('skill_name') == "ASCLEPIUS":
                actor = state.actor_data[a_id]
                if getattr(actor, 'mp_charge', 0) >= 1000:
                    executed.add(a_id)
                    for t_id, t_actor in state.actor_data.items():
                        if not t_actor.is_oni and self._l1_dist(actor.pos, t_actor.pos) <= 10:
                            status_updates[t_id].update({
                                "asclepius_active": True,
                                "asclepius_duration": 5,
                                "stamina_rate": 0.3
                            })
        return executed

    def _finalize_actions(self, state, status_updates, skill_executed):
        for a_id in skill_executed:
            if status_updates[a_id].get('alive', state.actor_data[a_id].alive):
                current_mp = state.actor_data[a_id].mp_charge
                status_updates[a_id]['mp_charge'] = current_mp - 1000

    def _resolve_items(self, final_positions, state, status_updates):
        taken_items = set()
        for a_id, pos in final_positions.items():
            if status_updates[a_id].get('alive') is False:
                continue

            pos_tuple = tuple(pos)
            if pos_tuple in taken_items: 
                continue

            item = state.grid_items.get(pos_tuple)
            if item:
                if item.type == "DOLL":
                    status_updates[a_id]['has_doll'] = True
                    status_updates.setdefault('removed_items', []).append(pos_tuple)
                    taken_items.add(pos_tuple)
                elif item.type == "MP_POTION":
                    actor = state.actor_data[a_id]
                    new_mp = min(actor.mp_charge + 500, 1000)
                    status_updates[a_id]['mp_charge'] = new_mp
                    status_updates.setdefault('removed_items', []).append(pos_tuple)
                    taken_items.add(pos_tuple)

    def _l1_dist(self, p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])