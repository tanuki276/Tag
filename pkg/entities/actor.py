import numpy as np
from pkg.entities.traits.memory import EntityMemory

class BaseActor:
    def __init__(self, a_id, pos, config):
        self.a_id = a_id
        self.pos = tuple(pos)
        self.prev_pos = tuple(pos)
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
            "alive": self.alive,
            "escaped": self.escaped
        }

    def commit_status(self, target_pos, status_update):
        if target_pos is not None:
            self.prev_pos = self.pos
            self.pos = tuple(target_pos)
        
        for attr, value in status_update.items():
            if hasattr(self, attr):
                setattr(self, attr, value)

    def tick(self):
        pass

class Human(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_human = True
        self.vision_range = config["entities"]["human"]["vision_range"]
        self.has_doll = config["entities"]["human"]["initial_dolls"] > 0
        self.stamina = 100
        self.dream_mode = 0
        self.invincible = False
        self.stun = 0

    def decide(self, view):
        if self.stun > 0 or not self.alive or self.escaped:
            return type('Intent', (), {
                "target_pos": self.pos, 
                "priority": 0, 
                "metadata": {}
            })
        
        return type('Intent', (), {
            "target_pos": self.pos, 
            "priority": self.config["entities"]["human"]["move_priority"],
            "metadata": {"ignore_walls": False}
        })

    def tick(self):
        if self.stun > 0:
            self.stun -= 1
        if self.dream_mode > 0:
            self.dream_mode -= 1

class Oni(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.vision_range = config["entities"]["oni"]["vision_range"]
        self.confused = 0

    def decide(self, view):
        if self.confused > 0 or not self.alive:
            return type('Intent', (), {
                "target_pos": self.pos, 
                "priority": 0, 
                "metadata": {}
            })

        return type('Intent', (), {
            "target_pos": self.pos, 
            "priority": self.config["entities"]["oni"]["move_priority"],
            "metadata": {"ignore_walls": False}
        })

    def tick(self):
        if self.confused > 0:
            self.confused -= 1
