from enum import Enum, auto

class ElementType(Enum):
    KEY = auto()
    EXIT = auto()
    TRAP = auto()
    DOLL = auto()

class MapElement:
    def __init__(self, e_type: ElementType, data: dict = None):
        self.type = e_type
        self.properties = data if data else {}
        self.discovered = False

    def interact(self, actor):
        self.discovered = True
        return self.type, self.properties
