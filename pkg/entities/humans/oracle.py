from pkg.entities.actor import Human

class Oracle(Human):
    def __init__(self, a_id, pos, config):
        super().__init__(a_id, pos, config)
        self.mp = config["entities"]["human"]["base_mp"]
        self.dream_mode = 0

    def decide(self, view):
        if self.dream_mode > 0:
            self.dream_mode -= 1
            # Special movement ignoring walls logic here

        return super().decide(view)