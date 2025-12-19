from pkg.entities.actor import BaseActor
import random

class Oni(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = True
        self.vision_range = config["entities"]["oni"]["vision_range"]
        self.confused = 0
        self.target_last_pos = None

    def decide(self, view):
        if self.confused > 0:
            self.confused -= 1
            return type('Intent', (), {"target_pos": self.pos, "priority": 0})

        visible_humans = [a for a in view.actors if not a["is_oni"] and a["alive"]]
        
        if visible_humans:
            # Target closest human
            target = min(visible_humans, key=lambda h: abs(h["pos"][0]-self.pos[0]) + abs(h["pos"][1]-self.pos[1]))
            self.target_last_pos = target["pos"]
        
        target_pos = self.target_last_pos if self.target_last_pos else self.pos
        
        # Speed logic (Dash)
        priority = self.config["entities"]["oni"]["move_priority"]
        if random.random() < self.config["entities"]["oni"]["dash_chance"]:
            priority += 5

        return type('Intent', (), {"target_pos": target_pos, "priority": priority})
