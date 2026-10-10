from typing import Any, Dict

from loguru import logger


class GameLogger:
    def __init__(self, level="DEBUG"):
        logger.remove()
        logger.add(lambda message: print(message, end=""), level=level, format="{time:HH:mm:ss.SSS} | {level: <8} | {message}")
        self.lib = logger

    def log_turn(self, turn: int, result: Any):
        snapshot = result.snapshot
        humans = [v for v in snapshot.values() if not v.get("is_oni")]
        alive = [h for h in humans if h.get("alive") and not h.get("escaped")]
        escaped = [h for h in humans if h.get("escaped")]
        captured = [a_id for a_id, action in result.actions.items() if action.status_update.get("alive") is False]
        self.lib.info(f"TURN_END | T: {turn:03} | HUM: {len(alive)}/{len(humans)} | ESC: {len(escaped)} | CAPTURED: {len(captured)}")

    def print_report(self, report: Dict[str, Any]):
        self.lib.info("=" * 40)
        self.lib.info(f"{'FINAL SIMULATION REPORT':^40}")
        self.lib.info("=" * 40)
        for key, value in report.items():
            rendered = f"{value:.6f}" if isinstance(value, float) else str(value)
            self.lib.info(f"{key: <25}: {rendered: >12}")
        self.lib.info("=" * 40)
