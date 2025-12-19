from collections import defaultdict

class ActionResolver:
    def __init__(self, config: dict):
        self.config = config

    def resolve(self, intents: dict, state: 'WorldState') -> dict:
        resolved = {}
        target_map = defaultdict(list)
        
        sorted_ids = sorted(
            intents.keys(), 
            key=lambda x: (not state.actor_data[x].is_oni, intents[x].priority), 
            reverse=True
        )

        for a_id in sorted_ids:
            target_map[intents[a_id].target_pos].append(a_id)

        occupied_positions = set(state.grid_walls)
        
        for pos, a_ids in target_map.items():
            winner_id = a_ids[0]
            winner_intent = intents[winner_id]
            
            if pos in occupied_positions:
                resolved[winner_id] = self._stay_action(winner_id, state)
                continue

            if len(a_ids) > 1:
                self._handle_conflict(winner_id, a_ids[1:], intents, resolved, state)
            else:
                resolved[winner_id] = winner_intent
                
            occupied_positions.add(pos)

        self._check_intercepts(intents, resolved, state)
        return resolved

    def _handle_conflict(self, winner_id, losers, intents, resolved, state):
        resolved[winner_id] = intents[winner_id]
        for l_id in losers:
            if state.actor_data[winner_id].is_oni and state.actor_data[l_id].is_human:
                resolved[l_id] = self._death_action(l_id)
            else:
                resolved[l_id] = self._stay_action(l_id, state)

    def _check_intercepts(self, intents, resolved, state):
        for a_id, intent in intents.items():
            if not state.actor_data[a_id].is_human:
                continue
            
            for o_id in [i for i in intents if state.actor_data[i].is_oni]:
                if intent.target_pos == state.actor_data[o_id].pos and \
                   intents[o_id].target_pos == state.actor_data[a_id].pos:
                    resolved[a_id] = self._death_action(a_id)

    def _stay_action(self, a_id, state):
        return type('Action', (), {'target_pos': state.actor_data[a_id].pos})

    def _death_action(self, a_id):
        return type('Action', (), {
            'target_pos': None, 
            'status_update': {'alive': False}
        })
