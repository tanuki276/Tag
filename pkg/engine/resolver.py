from collections import defaultdict

class ActionResolver:
    def __init__(self, config):
        self.config = config

    def resolve(self, intents, state):
        resolved = {}
        target_map = defaultdict(list)
        
        # Priority sort: Oni (High) > Human (Low)
        sorted_ids = sorted(
            intents.keys(), 
            key=lambda x: (state.actor_data[x].is_oni, intents[x].priority), 
            reverse=True
        )

        for a_id in sorted_ids:
            target_map[intents[a_id].target_pos].append(a_id)

        occupied_positions = set(zip(*np.where(state.grid == 1)))
        
        for pos, a_ids in target_map.items():
            winner_id = a_ids[0]
            if pos in occupied_positions:
                resolved[winner_id] = self._create_action(state.actor_data[winner_id].pos)
                continue

            resolved[winner_id] = intents[winner_id]
            
            if len(a_ids) > 1:
                for loser_id in a_ids[1:]:
                    if state.actor_data[winner_id].is_oni and not state.actor_data[loser_id].is_oni:
                        resolved[loser_id] = self._create_action(None, {"alive": False})
                    else:
                        resolved[loser_id] = self._create_action(state.actor_data[loser_id].pos)
            
            occupied_positions.add(pos)

        self._process_intercepts(intents, resolved, state)
        return resolved

    def _process_intercepts(self, intents, resolved, state):
        onis = [a_id for a_id, a in state.actor_data.items() if a.is_oni]
        humans = [a_id for a_id, a in state.actor_data.items() if not a.is_oni and a.alive]
        
        for h_id in humans:
            h_intent = intents.get(h_id)
            if not h_intent: continue
            
            for o_id in onis:
                o_intent = intents.get(o_id)
                if not o_intent: continue
                
                # Intercept logic: Cross-moving
                if h_intent.target_pos == state.actor_data[o_id].pos and \
                   o_intent.target_pos == state.actor_data[h_id].pos:
                    resolved[h_id] = self._create_action(None, {"alive": False})

    def _create_action(self, pos, status=None):
        return type('Action', (), {'target_pos': pos, 'status_update': status if status else {}})
