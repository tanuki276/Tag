import numpy as np
from pkg.schema.protocols import IActor
from pkg.entities.traits.memory import EntityMemory

class BaseActor:
    def __init__(self, a_id, pos, config):
        self.a_id = a_id
        self.pos = pos
        self.config = config
        self.alive = True
        self.escaped = False
        self.is_oni = False
        self.vision_range = 0
        self.memory = EntityMemory()

    def get_public_status(self):
        return {
            "a_id": self.a_id,
            "pos": self.pos,
            "is_oni": self.is_oni,
            "alive": self.alive
        }

class Human(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_human = True
        self.vision_range = config["entities"]["human"]["vision_range"]
        self.has_doll = config["entities"]["human"]["initial_dolls"] > 0
        self.stun = 0
        self.identifying = None

    def decide(self, view):
        if self.stun > 0:
            return type('Intent', (), {"target_pos": self.pos, "priority": 0})
        
        # Logic to be implemented in sub-classes or specialized traits
        return type('Intent', (), {"target_pos": self.pos, "priority": self.config["entities"]["human"]["move_priority"]})

class Oni(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.vision_range = config["entities"]["oni"]["vision_range"]
        self.confused = 0
        self.target_last_pos = None

    def decide(self, view):
        if self.confused > 0:
            return type('Intent', (), {"target_pos": self.pos, "priority": 0})
            
        # Logic to be implemented in sub-classes
        return type('Intent', (), {"target_pos": self.pos, "priority": self.config["entities"]["oni"]["move_priority"]})
