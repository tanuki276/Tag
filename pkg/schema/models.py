from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    MOVE = "MOVE"
    STAY = "STAY"
    SKILL = "SKILL"


class Priority(IntEnum):
    LOW = 0
    WAIT = 10
    MOVE_DEFAULT = 20
    SKILL_MID = 50
    SKILL_HIGH = 80
    URGENT = 100


class Element(BaseModel):
    pos: Tuple[int, int]
    kind: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class ActorStatus(BaseModel):
    a_id: str
    pos: Tuple[int, int]
    is_oni: bool
    alive: bool = True
    escaped: bool = False
    role: Optional[str] = None
    job: Optional[str] = None
    stamina: Optional[int] = None


class LocalView(BaseModel):
    pos: Tuple[int, int]
    actors: List[ActorStatus] = Field(default_factory=list)
    elements: List[Element] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(default_factory=dict)


class Intent(BaseModel):
    target_pos: Tuple[int, int]
    priority: int = int(Priority.MOVE_DEFAULT)
    action_type: ActionType = ActionType.MOVE
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    target_pos: Optional[Tuple[int, int]]
    status_update: Dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    turn: int
    intents: Dict[str, Intent]
    actions: Dict[str, Action]
    snapshot: Dict[str, Dict[str, Any]]
    is_terminal: bool
    termination_reason: str = ""


@runtime_checkable
class IGrid(Protocol):
    shape: Tuple[int, int]

    def is_walkable(self, pos: Tuple[int, int]) -> bool: ...
    def in_bounds(self, pos: Tuple[int, int]) -> bool: ...


@runtime_checkable
class IActor(Protocol):
    a_id: str
    pos: Tuple[int, int]
    is_oni: bool
    alive: bool
    escaped: bool

    def decide(self, view: LocalView) -> Intent: ...
    def get_public_status(self) -> ActorStatus: ...
    def commit_status(
        self, target_pos: Optional[Tuple[int, int]], status_update: Dict[str, Any]
    ) -> None: ...
    def tick(self) -> None: ...
