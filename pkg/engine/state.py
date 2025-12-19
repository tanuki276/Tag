import numpy as np
from pkg.schema.models import StateSnapshot, StepResult

class WorldState:
    def __init__(self, config: dict, grid: np.ndarray, actors: dict):
        self.config = config
        self.grid = grid
        self.actor_data = actors
        self.turn = 0
        self.is_terminal = False
        self.termination_reason = ""

    def apply(self, resolved_actions: dict) -> 'WorldState':
        for a_id, action in resolved_actions.items():
            actor = self.actor_data[a_id]
            actor.pos = action.target_pos
            if hasattr(action, 'status_update'):
                for attr, val in action.status_update.items():
                    setattr(actor, attr, val)
        
        self.turn += 1
        self._check_termination()
        return self

    def _check_termination(self):
        alive_humans = [r for r in self.actor_data.values() if r.is_human and r.alive and not r.escaped]
        if not alive_humans:
            self.is_terminal = True
            self.termination_reason = "ALL_HUMANS_ELIMINATED"
        elif self.turn >= self.config["world"]["max_turns"]:
            self.is_terminal = True
            self.termination_reason = "MAX_TURNS_REACHED"

    def export_step_result(self, intents: dict, resolved_actions: dict) -> StepResult:
        return StepResult(
            turn=self.turn,
            is_terminal=self.is_terminal,
            termination_reason=self.termination_reason,
            intents=intents,
            actions=resolved_actions,
            snapshot=self.actor_data
        )
