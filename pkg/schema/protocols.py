from typing import Protocol, Dict, Any, Tuple, runtime_checkable

@runtime_checkable
class IActor(Protocol):
    a_id: str
    pos: Tuple[int, int]
    is_oni: bool
    alive: bool
    escaped: bool

    def decide(self, view: LocalView) -> Intent:
        ...

    def get_public_status(self) -> Dict[str, Any]:
        ...

    def commit_status(self, target_pos: Tuple[int, int], status_update: Dict[str, Any]) -> None:
        ...

    def tick(self) -> None:
        ...

@runtime_checkable
class IState(Protocol):
    grid: Any
    actor_data: Dict[str, IActor]
    map_elements: Dict[Tuple[int, int], Any]
    turn: int
    is_terminal: bool
    termination_reason: str
    exit_open: bool
    exit_pos: Tuple[int, int]

    def apply(self, resolved_actions: Dict[str, Action]) -> 'IState':
        ...

    def export_step_result(self, intents: Dict[str, Intent], resolved_actions: Dict[str, Action]) -> StepResult:
        ...

@runtime_checkable
class IResolver(Protocol):
    def resolve(self, intents: Dict[str, Intent], state: IState) -> Dict[str, Action]:
        ...
