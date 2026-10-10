from pkg.engine.mediator import InformationMediator
from pkg.engine.resolver import ActionResolver


class SimulationCore:
    def __init__(self, state, config, learning_cfg):
        self.state = state
        self.config = config
        self.learning_cfg = learning_cfg
        self.mediator = InformationMediator(config)
        self.resolver = ActionResolver(config)

    def get_snapshot(self):
        return self.state.get_snapshot()

    def step(self):
        active = {
            a_id: actor
            for a_id, actor in self.state.actor_data.items()
            if actor.alive and not actor.escaped
        }
        views = self.mediator.get_local_views(self.state)
        intents = {a_id: actor.decide(views[a_id]) for a_id, actor in active.items()}
        resolved = self.resolver.resolve(intents, self.state)
        self.state.apply(resolved)

        if self.learning_cfg.get("meta_strategy", {}).get("enable_feedback_loop"):
            self.mediator.inject_learning(self.state, resolved)

        return self.state.export_step_result(intents, resolved)

    def run(self):
        results = []
        while not self.state.is_terminal:
            results.append(self.step())
        return results
