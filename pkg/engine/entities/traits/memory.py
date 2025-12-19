class EntityMemory:
    def __init__(self):
        self.known_elements = {}
        self.seen_actors = {}
        self.prediction_model = None

    def update_prediction_model(self, data):
        self.prediction_model = data

    def get_relevant(self, turn):
        return {
            "elements": self.known_elements,
            "actors": self.seen_actors,
            "prediction": self.prediction_model
        }
