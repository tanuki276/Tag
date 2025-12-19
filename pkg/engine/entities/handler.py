from typing import Dict, Any, Optional
from pkg.schema.models import IActor

class EntityStateHandler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def process_status_effects(self, actor: IActor) -> None:
        if hasattr(actor, 'stun') and actor.stun > 0:
            actor.stun -= 1

        if hasattr(actor, 'dream_mode') and actor.dream_mode > 0:
            actor.dream_mode -= 1
            if actor.dream_mode == 0:
                backlash = self.config["entities"]["human"].get("dream_backlash", 4)
                setattr(actor, 'stun', backlash)

    def apply_capture(self, victim: IActor) -> Dict[str, Any]:
        update = {"alive": False, "pos": None}
        victim.commit_status(None, update)
        return update

    def apply_confusion(self, oni: IActor, duration: int) -> None:
        setattr(oni, 'confused', duration)
