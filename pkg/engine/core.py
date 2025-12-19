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
        self.state = self.state.apply(resolved_actions)
        
        if self.learning_cfg.get("meta_strategy", {}).get("enable_feedback_loop"):
            self.mediator.inject_learning(self.state, resolved_actions)
            
        return self.state.export_step_result(intents, resolved_actions)
