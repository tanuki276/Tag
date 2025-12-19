import numpy as np
from collections import defaultdict
from pkg.schema.models import Action

class ActionResolver:
    def __init__(self, config):
        self.config = config

    def resolve(self, intents, state):
        sorted_ids = sorted(
            intents.keys(),
            key=lambda x: (intents[x].priority, state.actor_data[x].is_oni),
            reverse=True
        )

        reserved_moves = {}
        for a_id in sorted_ids:
            actor = state.actor_data[a_id]
            intent = intents[a_id]
            path = self._get_full_path(actor.pos, intent.target_pos)
            valid_pos = actor.pos
            ignore_walls = intent.metadata.get("ignore_walls", False)
            
            for cell in path[1:]:
                if not ignore_walls and (
                    cell[0] < 0 or cell[0] >= state.grid.shape[0] or 
                    cell[1] < 0 or cell[1] >= state.grid.shape[1] or 
                    state.grid[cell] == 1
                ):
                    break
                valid_pos = cell
            reserved_moves[a_id] = valid_pos

        final_positions = {}
        occupied_now = {a.pos for a in state.actor_data.values() if a.alive and not a.escaped}

        for a_id in sorted_ids:
            actor = state.actor_data[a_id]
            target = reserved_moves[a_id]
            
            if target == actor.pos:
                final_positions[a_id] = target
                continue

            if target in final_positions.values() or (target in occupied_now and target not in [state.actor_data[i].pos for i in sorted_ids if i not in final_positions]):
                final_positions[a_id] = actor.pos
            else:
                final_positions[a_id] = target

        resolved = {a_id: Action(target_pos=pos, status_update={}) 
                    for a_id, pos in final_positions.items()}

        self._resolve_combat(intents, resolved, state)
        self._resolve_items(resolved, state)

        return resolved

    def _resolve_combat(self, intents, resolved, state):
        onis = [a_id for a_id, a in state.actor_data.items() if a.is_oni]
        humans = [a_id for a_id, a in state.actor_data.items() if not a.is_oni and a.alive]

        for h_id in humans:
            h_actor = state.actor_data[h_id]
            if h_actor.invincible or not h_actor.alive: continue

            h_start = h_actor.pos
            h_end = resolved[h_id].target_pos
            if h_end is None: continue
            
            h_path = set(self._get_full_path(h_start, h_end))

            for o_id in onis:
                o_start = state.actor_data[o_id].pos
                o_end = resolved[o_id].target_pos
                o_path = set(self._get_full_path(o_start, o_end))

                if h_end == o_end or (h_path & o_path):
                    if not getattr(h_actor, 'has_doll', False):
                        resolved[h_id].target_pos = None
                        resolved[h_id].status_update["alive"] = False
                        break
                    else:
                        h_actor.has_doll = False
                        resolved[h_id].target_pos = h_start
                        break

    def _resolve_items(self, resolved, state):
        items_to_remove = set()
        for a_id, action in resolved.items():
            actor = state.actor_data[a_id]
            pos = action.target_pos
            if not pos or not getattr(actor, 'is_human', True) or pos not in state.map_elements:
                continue

            element = state.map_elements[pos]
            if getattr(actor, 'dream_mode', 0) > 0:
                if element.type.name == "KEY":
                    element.properties["identified"] = True
            else:
                if element.type.name == "KEY":
                    if element.properties.get("is_real"):
                        state.exit_open = True
                    items_to_remove.add(pos)
                elif element.type.name == "DOLL":
                    actor.has_doll = True
                    items_to_remove.add(pos)

        for pos in items_to_remove:
            if pos in state.map_elements:
                del state.map_elements[pos]

    def _get_full_path(self, p1, p2):
        path = [tuple(p1)]
        curr = list(p1)
        while tuple(curr) != tuple(p2):
            for i in range(2):
                if curr[i] != p2[i]:
                    curr[i] += 1 if p2[i] > curr[i] else -1
            path.append(tuple(curr))
        return path
