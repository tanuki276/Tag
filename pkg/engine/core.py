from pkg.schema.protocols import IState, IStepResult

class SimulationCore:
    def __init__(self, state: IState, config: dict, learning_cfg: dict):
        self.state = state
        self.config = config
        self.learning_cfg = learning_cfg
        self.mediator = None # To be implemented
        self.resolver = None # To be implemented

    def step(self) -> IStepResult:
        views = self.mediator.get_local_views(self.state)
        intents = {a_id: actor.decide(views[a_id]) for a_id, actor in self.state.actors.items()}
        resolved_actions = self.resolver.resolve(intents, self.state)
        self.state = self.state.apply(resolved_actions)
        return self.state.export_step_result(intents, resolved_actions)
