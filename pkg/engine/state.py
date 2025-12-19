import numpy as np

class WorldState:
    def __init__(self, config, grid, actors, map_elements):
        self.config = config
        self.grid = grid
        self.actor_data = actors
        self.map_elements = map_elements
        self.turn = 0
        self.is_terminal = False
        self.termination_reason = ""

    def apply(self, resolved_actions):
        for a_id, action in resolved_actions.items():
            actor = self.actor_data[a_id]
            if action.target_pos is not None:
                actor.prev_pos = actor.pos
                actor.pos = action.target_pos
            
            if hasattr(action, 'status_update'):
                for attr, val in action.status_update.items():
                    setattr(actor, attr, val)
        
        self.turn += 1
        self._check_termination()
        return self

    def _check_termination(self):
        humans = [a for a in self.actor_data.values() if not a.is_oni]
        alive_humans = [h for h in humans if h.alive and not h.escaped]
        
        if not alive_humans:
            self.is_terminal = True
            self.termination_reason = "ALL_HUMANS_ELIMINATED"
        elif self.turn >= self.config["world"]["max_turns"]:
            self.is_terminal = True
            self.termination_reason = "MAX_TURNS_REACHED"
        elif any(h.escaped for h in humans) and self.config["game_rules"].get("escape_enabled"):
            if len([h for h in humans if h.escaped]) == len(humans):
                self.is_terminal = True
                self.termination_reason = "ALL_HUMANS_ESCAPED"

    def export_step_result(self, intents, resolved_actions):
        from pkg.schema.models import StepResult
        return StepResult(
            turn=self.turn,
            is_terminal=self.is_terminal,
            termination_reason=self.termination_reason,
            intents=intents,
            actions=resolved_actions,
            snapshot={a_id: a.get_public_status() for a_id, a in self.actor_data.items()}
        )
