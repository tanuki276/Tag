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
        oni_ids = [a_id for a_id, a in res.snapshot.items() if a.get("is_oni")]
        human_ids = [a_id for a_id, a in res.snapshot.items() if not a.get("is_oni")]

        captures = [a_id for a_id, action in res.actions.items() 
                    if action.status_update.get('alive') is False]
        self.metrics["total_captures"] += len(captures)

        hits = 0
        for o_id in oni_ids:
            o_intent = res.intents.get(o_id)
            if not o_intent or not o_intent.target_pos:
                continue
            
            for h_id in human_ids:
                h_intent = res.intents.get(h_id)
                if h_intent and tuple(o_intent.target_pos) == tuple(h_intent.target_pos):
                    hits += 1

        self.metrics["prediction_hits"] += hits
        if oni_ids:
            self.metrics["intercept_precision"].append(hits / len(oni_ids))

    def generate_final_report(self):
        if not self.history:
            return {"error": "NO_HISTORY_DATA"}

        final_res = self.history[-1]
        final_state = final_res.snapshot
        humans = [h for h in final_state.values() if not h.get("is_oni")]
        escaped = [h for h in humans if h.get("escaped")]

        return {
            "turn_count": len(self.history),
            "termination_reason": final_res.termination_reason,
            "avg_intercept_precision": float(np.mean(self.metrics["intercept_precision"])) if self.metrics["intercept_precision"] else 0.0,
            "total_captures": self.metrics["total_captures"],
            "survival_rate": len(escaped) / len(humans) if humans else 0.0,
            "prediction_hit_rate": self.metrics["prediction_hits"] / len(self.history) if self.history else 0.0
        }
