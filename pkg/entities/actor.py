import copy

from pkg.entities.traits.memory import EntityMemory
from pkg.schema.models import ActorStatus


class BaseActor:
    def __init__(self, a_id, pos, config):
        self.a_id = str(a_id)
        self.pos = tuple(map(int, pos))
        self.prev_pos = self.pos
        self.config = config
        self.alive = True
        self.escaped = False
        self.is_oni = False
        self.vision_range = 5
        self.memory = EntityMemory()
        self.invincible = False
        self.stun = 0
        self.confused = 0
        self.slow_duration = 0

    def get_public_status(self):
        stamina = getattr(self, "stamina", None)
        return ActorStatus(
            a_id=self.a_id,
            pos=self.pos,
            is_oni=self.is_oni,
            alive=self.alive,
            escaped=self.escaped,
            role=getattr(self, "role", None),
            job=getattr(self, "job", None),
            stamina=int(stamina) if stamina is not None else None,
        )

    def get_status(self):
        return self.get_public_status().model_dump()

    def commit_status(self, target_pos, status_update):
        if target_pos is not None:
            self.prev_pos = self.pos
            self.pos = tuple(map(int, target_pos))

        for attr, value in status_update.items():
            if attr.startswith("_"):
                continue
            if hasattr(self, attr):
                setattr(self, attr, value)

    def tick(self):
        for attr in ("stun", "confused", "slow_duration"):
            value = getattr(self, attr, 0)
            if value > 0:
                setattr(self, attr, value - 1)

    def clone(self):
        return copy.deepcopy(self)
