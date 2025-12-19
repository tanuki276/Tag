import numpy as np

class EntityMemory:
    def __init__(self):
        self.known_elements = {}
        self.seen_actors = {}
        self.prediction_map = {}
        self.grid_map = None

    def update_prediction(self, a_id, pos):
        if a_id not in self.prediction_map:
            self.prediction_map[a_id] = []
        self.prediction_map[a_id].append(tuple(pos))
        if len(self.prediction_map[a_id]) > 10:
            self.prediction_map[a_id].pop(0)

    def get_relevant(self, turn):
        return {
            "elements": self.known_elements.copy(),
            "actors": self.seen_actors.copy(),
            "prediction_map": self.prediction_map.copy(),
            "grid_map": self.grid_map
        }

    def record_element(self, pos, element):
        self.known_elements[tuple(pos)] = {
            "type": element.type.name,
            "last_seen": tuple(pos),
            "properties": element.properties.copy()
        }

    def update_seen_actor(self, a_id, status, turn):
        self.seen_actors[a_id] = {
            "pos": tuple(status.get("pos")) if status.get("pos") else None,
            "is_oni": status.get("is_oni"),
            "last_turn": turn
        }
