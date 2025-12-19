from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Tuple

class LocalView(BaseModel):
    pos: Tuple[int, int]
    actors: List[Dict[str, Any]]
    elements: List[Tuple[Tuple[int, int], Any]]
    memory: Dict[str, Any]

class Intent(BaseModel):
    target_pos: Tuple[int, int]
    priority: int
    action_type: str = "MOVE"
    metadata: Dict[str, Any] = {}

class Action(BaseModel):
    target_pos: Optional[Tuple[int, int]]
    status_update: Dict[str, Any] = {}

class StepResult(BaseModel):
    turn: int
    is_terminal: bool
    termination_reason: str
    intents: Dict[str, Any]
    actions: Dict[str, Any]
    snapshot: Dict[str, Dict[str, Any]]

class ActorStatus(BaseModel):
    a_id: str
    pos: Optional[Tuple[int, int]]
    is_oni: bool
    alive: bool
    escaped: bool
