import numpy as np
from pkg.engine.mediator import InformationMediator
from pkg.engine.resolver import ActionResolver

class SimulationCore:
    def __init__(self, state, config, learning_cfg):
        self.state = state
        self.config = config
        self.learning_cfg = learning_cfg
        self.mediator = InformationMediator(config)
        self.resolver = ActionResolver(config)

    def step(self):
        views = self.mediator.get_local_views(self.state)
        
        intents = {
            a_id: actor.decide(views[a_id]) 
            for a_id, actor in self.state.actor_data.items() 
            if actor.alive and not actor.escaped
        }
        
        resolved_actions = self.resolver.resolve(intents, self.state)
        
        self._commit_state_updates(resolved_actions)

        if self.learning_cfg.get("meta_strategy", {}).get("enable_feedback_loop"):
            self.mediator.inject_learning(self.state, resolved_actions)

        self.state.turn += 1
        self._check_termination()

        return self.state.export_step_result(intents, resolved_actions)

    def _commit_state_updates(self, resolved_actions):
        for a_id, action in resolved_actions.items():
            actor = self.state.actor_data[a_id]
            
            if action.status_update.get("alive") is False:
                actor.alive = False
                continue
                
            if action.target_pos:
                actor.prev_pos = actor.pos
                actor.pos = action.target_pos
            
            actor.update_state()

    def _check_termination(self):
        humans = [a for a in self.state.actor_data.values() if not a.is_oni]
        
        if self.state.exit_open:
            for h in humans:
                if h.alive and not h.escaped and h.pos == self.state.exit_pos:
                    h.escaped = True
            
            active_humans = [h for h in humans if h.alive and not h.escaped]
            if not active_humans and any(h.escaped for h in humans):
                self.state.is_terminal = True
                self.state.termination_reason = "ALL_HUMANS_ESCAPED"
                return

        active_humans = [h for h in humans if h.alive and not h.escaped]
        if not active_humans:
            self.state.is_terminal = True
            self.state.termination_reason = "ALL_HUMANS_ELIMINATED"
            return

        if self.state.turn >= self.config["world"]["max_turns"]:
            self.state.is_terminal = True
            self.state.termination_reason = "MAX_TURNS_REACHED"
