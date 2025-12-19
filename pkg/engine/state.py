class WorldState:
    def __init__(self, grid, actor_data, map_elements, config):
        self.grid = grid
        self.actor_data = actor_data
        self.map_elements = map_elements
        self.config = config
        self.turn = 0
        self.is_terminal = False
        self.termination_reason = ""
        self.exit_open = False
        self.exit_pos = tuple(config["world"]["exit_pos"])

    def apply(self, resolved_actions):
        self.turn += 1

        for a_id, actor in self.actor_data.items():
            action = resolved_actions.get(a_id)
            if action:
                actor.commit_status(action.target_pos, action.status_update)
            actor.tick()

        self._check_termination()
        return self

    def _check_termination(self):
        humans = [a for a in self.actor_data.values() if not a.is_oni]
        
        if self.exit_open:
            for h in humans:
                if h.alive and not h.escaped and tuple(h.pos) == self.exit_pos:
                    h.escaped = True

        total_humans = len(humans)
        escaped_humans = [h for h in humans if h.escaped]
        alive_not_escaped = [h for h in humans if h.alive and not h.escaped]
        dead_humans = [h for h in humans if not h.alive]

        if not alive_not_escaped:
            self.is_terminal = True
            e_count = len(escaped_humans)
            
            if e_count == total_humans:
                self.termination_reason = "PERFECT_ESCAPE"
            elif e_count > 0:
                self.termination_reason = f"PARTIAL_ESCAPE_AND_DEATH (Escaped:{e_count}, Dead:{len(dead_humans)})"
            else:
                self.termination_reason = "TOTAL_ANNIHILATION"
            return

        if self.turn >= self.config["world"]["max_turns"]:
            self.is_terminal = True
            self.termination_reason = "MAX_TURNS_REACHED"

    def get_summary(self):
        return {
            "turn": self.turn,
            "alive": len([a for a in self.actor_data.values() if a.alive and not a.escaped]),
            "escaped": len([a for a in self.actor_data.values() if a.escaped]),
            "terminal": self.is_terminal
        }
