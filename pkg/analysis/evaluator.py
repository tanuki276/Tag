import numpy as np

class SimulationEvaluator:
    def __init__(self):
        self.history = []
        self.metrics = {
            "intercept_precision": [],
            "total_captures": 0,
            "prediction_hits": 0
        }

    def record_step(self, step_result):
        self.history.append(step_result)
        self._calculate_metrics(step_result)

    def _calculate_metrics(self, res):
        oni_ids = [a_id for a_id, a in res.snapshot.items() if a["is_oni"]]
        human_ids = [a_id for a_id, a in res.snapshot.items() if not a["is_oni"]]
        
        captures = [a for a in res.actions.values() if a.status_update.get('alive') is False]
        self.metrics["total_captures"] += len(captures)

        hits = 0
        for o_id in oni_ids:
            o_intent = res.intents.get(o_id)
            if not o_intent: continue
            for h_id in human_ids:
                h_intent = res.intents.get(h_id)
                if h_intent and o_intent.target_pos == h_intent.target_pos:
                    hits += 1
        
        self.metrics["prediction_hits"] += hits
        if oni_ids:
            self.metrics["intercept_precision"].append(hits / len(oni_ids))

    def generate_final_report(self):
        final_state = self.history[-1].snapshot
        humans = [h for h in final_state.values() if not h["is_oni"]]
        escaped = [h for h in humans if h["escaped"]]
        
        return {
            "avg_intercept_precision": float(np.mean(self.metrics["intercept_precision"])) if self.metrics["intercept_precision"] else 0.0,
            "total_captures": self.metrics["total_captures"],
            "survival_rate": len(escaped) / len(humans) if humans else 0.0
        }
