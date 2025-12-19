from enum import Enum, auto
from typing import Dict, Any, Tuple, Optional
from pkg.schema.models import Element

class ElementType(Enum):
    KEY = auto()
    EXIT = auto()
    TRAP = auto()
    DOLL = auto()

class ElementInteractor:
    @staticmethod
    def interact(element: Element, actor: Any) -> Tuple[str, Dict[str, Any]]:
        element.properties["discovered"] = True
        
        if element.kind == ElementType.TRAP.name:
            return "TRAP_TRIGGERED", {"alive": False}
            
        if element.kind == ElementType.KEY.name:
            return "KEY_PICKED", {"has_key": True}
            
        if element.kind == ElementType.EXIT.name:
            return "EXIT_REACHED", {"can_escape": True}
            
        return "NONE", {}
