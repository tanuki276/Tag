import numpy as np
from typing import List, Tuple, Dict, Any
from pkg.schema.models import IActor

class EffectCalculator:
    @staticmethod
    def calculate_fear_debuff(human_pos: Tuple[int, int], onis: List[IActor], config: Dict[str, Any]) -> float:
        fear_radius = config["human_adaptation"]["fear_radius"]
        h_p = np.array(human_pos)
        
        nearby_count = 0
        for o in onis:
            if o.pos is None:
                continue
            if np.linalg.norm(h_p - np.array(o.pos), ord=1) <= fear_radius:
                nearby_count += 1

        if nearby_count == 0:
            return 1.0
        return max(0.5, 1.0 - (nearby_count * 0.2))

    @staticmethod
    def is_intercepted(h_prev: Tuple[int, int], h_next: Tuple[int, int], o_prev: Tuple[int, int], o_next: Tuple[int, int]) -> bool:
        return h_prev == o_next and h_next == o_prev
