import random
import numpy as np

class RandomManager:
    def __init__(self, seed: int = None):
        self.seed = seed
        self.reset(seed)

    def reset(self, seed):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def get_state(self):
        return {
            "random": random.getstate(),
            "numpy": np.random.get_state()
        }

    def set_state(self, state):
        random.setstate(state["random"])
        np.random.set_state(state["numpy"])
