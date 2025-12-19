from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Any
from pydantic import BaseModel, Field

class ActionType(Enum):
    MOVE = auto()
    STAY = auto()
    SKILL = auto()

class Priority(Enum):
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
    hp: int = 100

class Memory(BaseModel):
    short_term: Dict[str, Any] = Field(default_factory=dict)
    long_term: Dict[str, Any] = Field(default_factory=dict)
    predictions: Dict[str, Tuple[int, int]] = Field(default_factory=dict)

class LocalView(BaseModel):
    pos: Tuple[int, int]
    actors: List[ActorStatus]
    elements: List[Element]
    memory: Memory

class Intent(BaseModel):
    target_pos: Tuple[int, int]
    priority: Priority = Priority.MOVE_DEFAULT
    action_type: ActionType = ActionType.MOVE
    metadata: Dict[str, Any] = Field(default_factory=dict)
