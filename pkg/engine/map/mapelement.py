from enum import Enum, auto

class ElementType(Enum):
    KEY = auto()
    EXIT = auto()
    TRAP = auto()

class MapElement:
    def __init__(self, e_type: ElementType, data: dict = None):
        self.type = e_type
        self.data = data if data else {}
        self.discovered = False

    def interact(self, actor):
        return self.type, self.data
