from collections import defaultdict

from pkg.engine.pathfinder import Pathfinder
from pkg.schema.models import Action, ActionType


class ActionResolver:
    def __init__(self, config):
        self.config = config

    def resolve(self, intents, state):
        pathfinder = Pathfinder(state.grid)
        status = defaultdict(dict)
        self._tick_buffs(state, status)
        self._resolve_skills(intents, state, status, pathfinder)
        sorted_ids = sorted(intents, key=lambda a_id: (int(intents[a_id].priority), state.actor_data[a_id].is_oni), reverse=True)
        final_positions, planned_paths = self._resolve_movement(sorted_ids, intents, state, status, pathfinder)
        self._resolve_combat(final_positions, planned_paths, state, status, pathfinder)
        self._resolve_items(final_positions, state, status)
        self._resolve_stamina(intents, final_positions, state, status)
        return {a_id: Action(target_pos=tuple(final_positions.get(a_id, state.actor_data[a_id].pos)), status_update=dict(status[a_id])) for a_id in intents}

    def _tick_buffs(self, state, status):
        for a_id, actor in state.actor_data.items():
            duration = getattr(actor, "asclepius_duration", 0)
            if duration > 0:
                duration -= 1
                status[a_id]["asclepius_duration"] = duration
                if duration == 0:
                    status[a_id]["asclepius_active"] = False
                    status[a_id]["stamina_rate"] = 1.0

    def _resolve_skills(self, intents, state, status, pathfinder):
        for a_id, intent in intents.items():
            if intent.action_type != ActionType.SKILL:
                continue
            actor = state.actor_data[a_id]
            name = str(intent.metadata.get("skill_name", "")).lower()
            cost = int(intent.metadata.get("mp_cost", 0))
            current_mp = int(getattr(actor, "mp_charge", 0))
            if current_mp < cost:
                continue
            if name == "asclepius":
                params = intent.metadata.get("params", {})
                radius = int(params.get("range", 10))
                duration = int(params.get("duration", 10))
                save = float(params.get("stamina_save", 0.70))
                for target_id, target in state.actor_data.items():
                    if target.is_oni or not target.alive or target.escaped:
                        continue
                    if self._l1(actor.pos, target.pos) <= radius and pathfinder.has_los(actor.pos, target.pos):
                        status[target_id].update({"asclepius_active": True, "asclepius_duration": duration, "stamina_rate": max(0.1, 1.0-save)})
                status[a_id]["mp_charge"] = current_mp - cost
            elif name == "negative_chain_reaction":
                target_id = intent.metadata.get("target_id")
                target = state.actor_data.get(target_id)
                if target is None or not target.is_oni or not target.alive:
                    continue
                params = intent.metadata.get("params", {})
                slow_duration = int(params.get("slow_duration", 6))
                chain_range = int(params.get("chain_range", 5))
                status[target_id]["slow_duration"] = max(getattr(target, "slow_duration", 0), slow_duration)
                status[target_id]["confused"] = max(getattr(target, "confused", 0), 1)
                for other_id, other in state.actor_data.items():
                    if other_id != target_id and other.is_oni and other.alive and self._l1(target.pos, other.pos) <= chain_range:
                        status[other_id]["slow_duration"] = max(getattr(other, "slow_duration", 0), max(1, slow_duration//2))
                status[a_id]["mp_charge"] = current_mp - cost

    def _resolve_movement(self, sorted_ids, intents, state, status, pathfinder):
        final_positions, planned_paths = {}, {}
        occupied = {tuple(actor.pos) for actor in state.actor_data.values() if actor.alive and not actor.escaped}
        reserved = set()
        for a_id in sorted_ids:
            actor = state.actor_data[a_id]
            current = tuple(actor.pos)
            occupied.discard(current)
            intent = intents[a_id]
            speed = 0 if intent.action_type in {ActionType.SKILL, ActionType.STAY} else 1
            if not actor.is_oni and intent.metadata.get("dash") and getattr(actor, "stamina", 0) >= int(intent.metadata.get("stamina_cost", 10)):
                speed = 2
            if status[a_id].get("asclepius_active") or getattr(actor, "asclepius_active", False):
                speed = max(speed, 2)
            if actor.is_oni and getattr(actor, "slow_duration", 0) > 0 and state.turn % 2 == 0:
                speed = 0
            if getattr(actor, "confused", 0) > 0:
                speed = 0
            path = pathfinder.get_path(current, tuple(intent.target_pos))
            path = path[:speed+1] if speed > 0 else [current]
            while len(path) > 1 and (path[-1] in occupied or path[-1] in reserved):
                path.pop()
            final = tuple(path[-1])
            final_positions[a_id] = final
            planned_paths[a_id] = path
            reserved.add(final)
        return final_positions, planned_paths

    def _resolve_combat(self, final_positions, planned_paths, state, status, pathfinder):
        oni_ids = [a_id for a_id,a in state.actor_data.items() if a.is_oni and a.alive and not a.escaped and a_id in final_positions]
        human_ids = [a_id for a_id,a in state.actor_data.items() if not a.is_oni and a.alive and not a.escaped and a_id in final_positions]
        for human_id in human_ids:
            human = state.actor_data[human_id]
            if getattr(human, "invincible", False):
                continue
            h_path = [tuple(p) for p in planned_paths[human_id]]
            for oni_id in oni_ids:
                o_path = [tuple(p) for p in planned_paths[oni_id]]
                collision = final_positions[human_id] == final_positions[oni_id]
                if not collision and len(h_path) > 1 and len(o_path) > 1:
                    collision = h_path[0] == o_path[1] and h_path[1] == o_path[0]
                if not collision:
                    collision = bool(set(h_path[1:]) & set(o_path[1:]))
                if collision and pathfinder.has_los(h_path[0], o_path[0]):
                    if getattr(human, "has_doll", False):
                        status[human_id]["has_doll"] = False
                    else:
                        status[human_id]["alive"] = False
                    final_positions[human_id] = h_path[0]
                    break

    def _resolve_items(self, final_positions, state, status):
        claimed = set()
        identify_time = int(state.config["game_rules"].get("identify_time", 3))
        for a_id, pos in final_positions.items():
            actor = state.actor_data[a_id]
            if actor.is_oni or status[a_id].get("alive", actor.alive) is False or pos in claimed:
                continue
            item = state.grid_items.get(tuple(pos))
            if item is None:
                continue
            if item.kind == "DOLL":
                status[a_id]["has_doll"] = True
            elif item.kind == "MP_POTION" and hasattr(actor, "mp_charge"):
                current = int(status[a_id].get("mp_charge", actor.mp_charge))
                status[a_id]["mp_charge"] = min(current+500, actor.max_mp_charge)
            elif item.kind == "KEY":
                pending = list(getattr(actor, "pending_keys", []))
                pending.append({"remaining": max(1, identify_time), "real": bool(item.properties.get("real", False))})
                status[a_id]["pending_keys"] = pending
            else:
                continue
            status[a_id].setdefault("_consume_items", []).append(tuple(pos))
            claimed.add(tuple(pos))

    def _resolve_stamina(self, intents, final_positions, state, status):
        for a_id, intent in intents.items():
            actor = state.actor_data[a_id]
            if actor.is_oni or not hasattr(actor, "stamina"):
                continue
            current = int(getattr(actor, "stamina", 100))
            moved = tuple(final_positions[a_id]) != tuple(actor.pos)
            if moved and intent.action_type == ActionType.MOVE:
                cost = int(intent.metadata.get("stamina_cost", getattr(actor, "walk_cost", 2)))
                rate = float(status[a_id].get("stamina_rate", getattr(actor, "stamina_rate", 1.0)))
                current = max(0, current - max(1, int(round(cost*rate))))
            elif intent.action_type != ActionType.SKILL:
                current = min(int(getattr(actor, "max_stamina", 100)), current + int(getattr(actor, "recover_rate", 5)))
            status[a_id]["stamina"] = current

    @staticmethod
    def _l1(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])
