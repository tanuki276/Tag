from loguru import logger
import sys
from typing import Dict, Any

class GameLogger:
    def __init__(self, level="DEBUG"):
        logger.remove()
        logger.add(
            sys.stderr, 
            level=level, 
            format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"
        )
        self.lib = logger

    def debug_decision(self, a_id: str, action: str, pos: tuple, reason: str = "N/A"):
        self.lib.debug(f"DECISION | ID: {a_id: <8} | ACT: {action: <6} | POS: {pos} | REASON: {reason}")

    def log_interaction(self, pos: tuple, interaction_type: str, participants: list):
        self.lib.info(f"INTERACT | POS: {pos} | TYPE: {interaction_type: <10} | ACTORS: {participants}")

    def log_status_change(self, a_id: str, trait: str, old: Any, new: Any):
        self.lib.warning(f"UPDATE   | ID: {a_id: <8} | TRAIT: {trait: <10} | {old} -> {new}")

    def log_turn(self, turn: int, res: Any):
        snapshot = res.snapshot
        oni_ids = [k for k, v in snapshot.items() if v.get("is_oni")]
        human_ids = [k for k, v in snapshot.items() if not v.get("is_oni")]
        
        alive_humans = [h for h in human_ids if snapshot[h].get("alive") and not snapshot[h].get("escaped")]
        captured_this_turn = [a_id for a_id, a in res.actions.items() if a.status_update.get('alive') is False]

        self.lib.info(f"TURN_END | T: {turn:03} | ONI: {len(oni_ids)} | HUM: {len(alive_humans)}/{len(human_ids)} | CAPTURED: {len(captured_this_turn)}")

    def print_report(self, report: Dict[str, Any]):
        self.lib.info("=" * 40)
        self.lib.info(f"{'FINAL SIMULATION REPORT':^40}")
        self.lib.info("=" * 40)
        for k, v in report.items():
            val = f"{v:.6f}" if isinstance(v, float) else str(v)
            self.lib.info(f"{k: <25}: {val: >12}")
        self.lib.info("=" * 40)
