from pkg.schema.models import StepResult


class WorldState:
    def __init__(self, grid, actor_data, map_elements, config, exit_pos):
        self.grid = grid
        self.actor_data = actor_data
        self.grid_items = dict(map_elements)
        self.config = config
        self.turn = 0
        self.is_terminal = False
        self.termination_reason = ""
        self.exit_open = False
        self.exit_pos = tuple(map(int, exit_pos))

    def apply(self, resolved_actions):
        self.turn += 1
        consumed = set()

        for a_id, actor in self.actor_data.items():
            action = resolved_actions.get(a_id)
            if action is not None:
                updates = dict(action.status_update)
                consumed.update(tuple(p) for p in updates.pop("_consume_items", []))
                actor.commit_status(action.target_pos, updates)
            actor.tick()

        for pos in consumed:
            item = self.grid_items.get(pos)
            if item is not None and item.kind != "EXIT":
                self.grid_items.pop(pos, None)

        self._check_exit_condition()
        self._check_termination()
        return self

    def _check_exit_condition(self):
        if not self.exit_open:
            required = int(self.config["game_rules"].get("num_keys_needed", 0))
            identified = sum(
                int(getattr(actor, "keys_identified", 0))
                for actor in self.actor_data.values()
                if not actor.is_oni
            )
            if identified >= required:
                self.exit_open = True

        if self.exit_open:
            for actor in self.actor_data.values():
                if (
                    not actor.is_oni
                    and actor.alive
                    and not actor.escaped
                    and tuple(actor.pos) == self.exit_pos
                ):
                    actor.escaped = True

    def _check_termination(self):
        humans = [a for a in self.actor_data.values() if not a.is_oni]
        active = [h for h in humans if h.alive and not h.escaped]
        escaped = [h for h in humans if h.escaped]

        if not active:
            self.is_terminal = True
            if len(escaped) == len(humans):
                self.termination_reason = "PERFECT_ESCAPE"
            elif escaped:
                self.termination_reason = "PARTIAL_ESCAPE_AND_DEATH"
            else:
                self.termination_reason = "TOTAL_ANNIHILATION"
            return

        if self.turn >= int(self.config["world"]["max_turns"]):
            self.is_terminal = True
            self.termination_reason = "MAX_TURNS_REACHED"

    def get_snapshot(self):
        snapshot = {}
        for a_id, actor in self.actor_data.items():
            data = actor.get_public_status().model_dump()
            for attr in (
                "has_doll",
                "keys_identified",
                "mp_charge",
                "asclepius_active",
                "slow_duration",
            ):
                if hasattr(actor, attr):
                    data[attr] = getattr(actor, attr)
            snapshot[a_id] = data
        return snapshot

    def export_step_result(self, intents, resolved_actions):
        return StepResult(
            turn=self.turn,
            intents=intents,
            actions=resolved_actions,
            snapshot=self.get_snapshot(),
            is_terminal=self.is_terminal,
            termination_reason=self.termination_reason,
        )

    def get_summary(self):
        humans = [a for a in self.actor_data.values() if not a.is_oni]
        return {
            "turn": self.turn,
            "alive_in_field": len([h for h in humans if h.alive and not h.escaped]),
            "escaped": len([h for h in humans if h.escaped]),
            "dead": len([h for h in humans if not h.alive]),
            "exit_open": self.exit_open,
            "identified_keys": sum(getattr(h, "keys_identified", 0) for h in humans),
            "terminal": self.is_terminal,
            "reason": self.termination_reason,
        }
