import numpy as np

class EffectCalculator:
    @staticmethod
    def calculate_fear_debuff(human_pos, onis, config):
        fear_radius = config["human_adaptation"]["fear_radius"]
        nearby_onis = [o for o in onis if np.linalg.norm(np.array(human_pos) - np.array(o.pos), ord=1) <= fear_radius]
        
        if not nearby_onis:
            return 1.0
        return max(0.5, 1.0 - (len(nearby_onis) * 0.2))

    @staticmethod
    def is_intercepted(h_prev, h_next, o_prev, o_next):
        return h_prev == o_next and h_next == o_prev
