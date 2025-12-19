import numpy as np

class WorldState:
    def __init__(self, grid, actor_data, map_elements, config):
        self.grid = grid
        self.actor_data = actor_data
        self.grid_items = map_elements.get("items", {})
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
        self._check_exit_condition()
        self._check_termination()
        return self

    def get_local_view(self, a_id, pathfinder):
        actor = self.actor_data[a_id]
        # 占い師(Oracle)なら視界を広げる、またはLoSを一部無視する
        is_oracle = getattr(actor, 'job', '') == 'ORACLE'
        vision_range = self.config["entities"].get("oracle_vision", 15) if is_oracle else 8 

        visible_actors = []
        for other_id, other_a in self.actor_data.items():
            if a_id == other_id or not other_a.alive or other_a.escaped:
                continue
            
            dist = pathfinder._dist(actor.pos, other_a.pos)
            if dist <= vision_range:
                # LoS判定: 占い師は壁越しでも「位置のみ」把握できる設定
                if is_oracle or pathfinder.has_los(actor.pos, other_a.pos):
                    visible_actors.append(other_a.get_status())
        
        visible_items = {
            pos: item for pos, item in self.grid_items.items()
            if pathfinder._dist(actor.pos, pos) <= vision_range and pathfinder.has_los(actor.pos, pos)
        }

        return {
            "pos": actor.pos,
            "actors": visible_actors,
            "items": visible_items,
            "exit_pos": self.exit_pos if self.exit_open else None,
            "grid_snippet": self.grid # 本来は周囲のみ切り出すべきだが現状維持
        }

    def _check_exit_condition(self):
        if not self.exit_open:
            return
        for a_id, actor in self.actor_data.items():
            if not actor.is_oni and actor.alive and not actor.escaped:
                if tuple(actor.pos) == self.exit_pos:
                    actor.escaped = True

    def _check_termination(self):
        humans = [a for a in self.actor_data.values() if not a.is_oni]
        total_humans = len(humans)
        alive_not_escaped = [h for h in humans if h.alive and not h.escaped]
        escaped_humans = [h for h in humans if h.escaped]

        if not alive_not_escaped:
            self.is_terminal = True
            e_count = len(escaped_humans)
            if e_count == total_humans:
                self.termination_reason = "PERFECT_ESCAPE"
            elif e_count > 0:
                self.termination_reason = "PARTIAL_ESCAPE_AND_DEATH"
            else:
                self.termination_reason = "TOTAL_ANNIHILATION"
            return

        if self.turn >= self.config["world"]["max_turns"]:
            self.is_terminal = True
            self.termination_reason = "MAX_TURNS_REACHED"

    def get_summary(self):
        return {
            "turn": self.turn,
            "alive_in_field": len([a for a in self.actor_data.values() if a.alive and not a.escaped]),
            "escaped": len([a for a in self.actor_data.values() if a.escaped]),
            "dead": len([a for a in self.actor_data.values() if not a.is_oni and not a.alive]),
            "terminal": self.is_terminal,
            "reason": self.termination_reason
        }
