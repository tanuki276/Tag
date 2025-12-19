import numpy as np
from enum import Enum
from typing import List, Dict, Tuple, Optional
from pkg.schema.models import LocalView, Intent, ActionType, Priority, ActorStatus, Element

class BaseAgentAI:
    def __init__(self, a_id: str, config: Dict):
        self.a_id = a_id
        self.config = config

    def decide(self, view: LocalView) -> Intent:
        raise NotImplementedError

class HumanAgentAI(BaseAgentAI):
    def decide(self, view: LocalView) -> Intent:
        oni_list = [a for a in view.actors if a.is_oni]
        
        if oni_list:
            return self._evade(view, oni_list)
        
        target_element = self._find_priority_element(view.elements)
        if target_element:
            return Intent(
                target_pos=target_element.pos,
                priority=Priority.MOVE_DEFAULT,
                action_type=ActionType.MOVE
            )
        
        return self._explore(view)

    def _evade(self, view: LocalView, onis: List[ActorStatus]) -> Intent:
        curr_y, curr_x = view.pos
        diff_y, diff_x = 0, 0
        
        for oni in onis:
            oy, ox = oni.pos
            dist = max(1, abs(curr_y - oy) + abs(curr_x - ox))
            diff_y += (curr_y - oy) / dist
            diff_x += (curr_x - ox) / dist
            
        target_pos = (
            int(round(curr_y + np.sign(diff_y))),
            int(round(curr_x + np.sign(diff_x)))
        )
        
        return Intent(
            target_pos=target_pos,
            priority=Priority.SKILL_HIGH,
            action_type=ActionType.MOVE,
            metadata={"reason": "evasion"}
        )

    def _find_priority_element(self, elements: List[Element]) -> Optional[Element]:
        for kind in ["EXIT", "KEY", "MP_POTION"]:
            found = [e for e in elements if e.kind == kind]
            if found:
                return found[0]
        return None

    def _explore(self, view: LocalView) -> Intent:
        if "target_path" in view.memory.short_term:
            return Intent(target_pos=view.memory.short_term["target_path"])
            
        h, w = view.memory.long_term.get("grid_shape", (30, 30))
        ty, tx = np.random.randint(0, h), np.random.randint(0, w)
        
        return Intent(
            target_pos=(ty, tx),
            priority=Priority.WAIT,
            action_type=ActionType.MOVE
        )

class OniAgentAI(BaseAgentAI):
    def decide(self, view: LocalView) -> Intent:
        humans = [a for a in view.actors if not a.is_oni and a.alive]
        
        if humans:
            target = min(humans, key=lambda h: abs(h.pos[0]-view.pos[0]) + abs(h.pos[1]-view.pos[1]))
            return Intent(
                target_pos=target.pos,
                priority=Priority.SKILL_MID,
                action_type=ActionType.MOVE,
                metadata={"target_id": target.a_id}
            )
            
        prediction = view.memory.predictions
        if prediction:
            latest_p = list(prediction.values())[0]
            return Intent(target_pos=latest_p, priority=Priority.MOVE_DEFAULT)

        return self._patrol(view)

    def _patrol(self, view: LocalView) -> Intent:
        curr_y, curr_x = view.pos
        directions = [(0, 2), (0, -2), (2, 0), (-2, 0)]
        move = directions[np.random.randint(0, 4)]
        
        return Intent(
            target_pos=(curr_y + move[0], curr_x + move[1]),
            priority=Priority.WAIT,
            action_type=ActionType.MOVE
        )
