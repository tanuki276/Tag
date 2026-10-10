class EntityMemory:
    def __init__(self):
        self.known_elements = {}
        self.seen_actors = {}
        self.prediction_map = {}

    def update_prediction(self, a_id, pos):
        history = self.prediction_map.setdefault(a_id, [])
        history.append(tuple(map(int, pos)))
        if len(history) > 10:
            history.pop(0)

    def get_relevant(self, turn):
        return {
            "elements": self.known_elements.copy(),
            "actors": self.seen_actors.copy(),
            "prediction_map": {k: v.copy() for k, v in self.prediction_map.items()},
            "current_turn": turn,
        }

    def record_element(self, pos, element):
        self.known_elements[tuple(pos)] = {
            "kind": element.kind,
            "last_seen": tuple(pos),
            "properties": element.properties.copy(),
        }

    def update_seen_actor(self, a_id, status, turn):
        self.seen_actors[a_id] = {
            "pos": tuple(status.pos),
            "is_oni": status.is_oni,
            "last_turn": turn,
            "role": status.role,
            "job": status.job,
        }
