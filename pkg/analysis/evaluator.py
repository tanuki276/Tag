import numpy as np
from pkg.schema.models import StepResult

class SimulationEvaluator:
    def __init__(self):
        self.history = []
        self.metrics = {
            "intercept_precision": [],
            "survival_prediction_error": [],
            "map_deadlock_index": [],
            "total_captures": 0,
            "prediction_hits": 0
        }

    def record_step(self, step_result: StepResult):
        self.history.append(step_result)
        self._calculate_prediction_metrics(step_result)
        self._calculate_map_deadlock(step_result)

    def _calculate_prediction_metrics(self, res: StepResult):
        oni_intents = [i for a_id, i in res.intents.items() if "O" in str(a_id)]
        human_intents = [i for a_id, i in res.intents.items() if "H" in str(a_id)]
        
        hits = 0
        for oi in oni_intents:
            for hi in human_intents:
                if oi.target_pos == hi.target_pos:
                    hits += 1
        
        self.metrics["prediction_hits"] += hits
        if oni_intents:
            self.metrics["intercept_precision"].append(hits / len(oni_intents))

    def _calculate_map_deadlock(self, res: StepResult):
        captures = [a_id for a_id, act in res.actions.items() if hasattr(act, 'status_update') and not act.status_update.get('alive', True)]
        self.metrics["total_captures"] += len(captures)
        
        # Deadlock defined as capture when all human moves were in Oni's range
        # Logic to be refined with distance map integration
        pass

    def generate_final_report(self) -> dict:
        return {
            "avg_intercept_precision": np.mean(self.metrics["intercept_precision"]) if self.metrics["intercept_precision"] else 0,
            "total_captures": self.metrics["total_captures"],
            "prediction_hit_rate": self.metrics["prediction_hit_rate"] if hasattr(self, "prediction_hit_rate") else 0,
            "survival_rate": self._calculate_survival_rate()
        }

    def _calculate_survival_rate(self) -> float:
        if not self.history: return 0.0
        final_state = self.history[-1].snapshot
        humans = [h for h in final_state.values() if "H" in h.a_id]
        escaped = [h for h in humans if h.escaped]
        return len(escaped) / len(humans) if humans else 0.0
