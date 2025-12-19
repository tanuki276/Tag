import numpy as np

class EntityMemory:
    def __init__(self):
        self.known_elements = {}
        self.seen_actors = {}
        self.prediction_map = {}
        self.grid_map = None

    def update_prediction_model(self, data):
        for a_id, pos in data.items():
            if a_id not in self.prediction_map:
                self.prediction_map[a_id] = []
            self.prediction_map[a_id].append(pos)
            if len(self.prediction_map[a_id]) > 10:
                self.prediction_map[a_id].pop(0)

    def get_relevant(self, turn):
        return {
            "elements": self.known_elements,
            "actors": self.seen_actors,
            "prediction_map": self.prediction_map,
            "grid_map": self.grid_map
        }

    def record_element(self, pos, element):
        self.known_elements[pos] = {
            "type": element.type.name,
            "last_seen": pos,
            "properties": element.properties
        }

    def update_seen_actor(self, a_id, status, turn):
        self.seen_actors[a_id] = {
            "pos": status.get("pos"),
            "is_oni": status.get("is_oni"),
            "last_turn": turn
        }
