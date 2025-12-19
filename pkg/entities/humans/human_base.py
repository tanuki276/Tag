from pkg.entities.actor import BaseActor

class Human(BaseActor):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.is_oni = False
        self.is_human = True
        self.vision_range = config["entities"]["human"]["vision_range"]
        self.has_doll = config["entities"]["human"]["initial_dolls"] > 0
        self.stun = 0
        self.identifying = None
        self.known_fakes = set()
        self.known_exit = None

    def _update_knowledge(self, view):
        for pos, element in view.elements:
            if element.type.name == "EXIT":
                self.known_exit = pos
        if view.memory:
            self.known_fakes.update(view.memory.get("fakes", []))

    def decide(self, view):
        self._update_knowledge(view)
        if self.stun > 0:
            return type('Intent', (), {"target_pos": self.pos, "priority": 0})
        
        # Grid-based movement logic (Simplified for structural overview)
        target_pos = self.pos # Placeholder for pathfinding result
        return type('Intent', (), {
            "target_pos": target_pos, 
            "priority": self.config["entities"]["human"]["move_priority"]
        })
