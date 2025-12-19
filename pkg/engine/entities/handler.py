class EntityStateHandler:
    def __init__(self, config: dict):
        self.config = config

    def process_status_effects(self, actor):
        if hasattr(actor, 'stun') and actor.stun > 0:
            actor.stun -= 1
        
        if hasattr(actor, 'dream_mode') and actor.dream_mode > 0:
            actor.dream_mode -= 1
            if actor.dream_mode == 0:
                actor.stun = self.config["entities"]["human"].get("dream_backlash", 4)

    def apply_capture(self, victim):
        victim.alive = False
        victim.pos = None
        return {"alive": False}

    def apply_confusion(self, oni, duration: int):
        oni.confused = duration
