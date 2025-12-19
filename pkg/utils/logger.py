from loguru import logger
import sys

class GameLogger:
    def __init__(self, level="INFO"):
        logger.remove()
        logger.add(
            sys.stderr, 
            level=level, 
            format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
        )
        self.lib = logger

    def info(self, msg):
        self.lib.info(msg)

    def error(self, msg):
        self.lib.error(msg)

    def log_turn(self, turn, res):
        alive = len([a for a in res.snapshot.values() if not a.get("is_oni") and a.get("alive") and not a.get("escaped")])
        captures = len([a_id for a_id, a in res.actions.items() if a.status_update.get('alive') is False])
        
        msg = f"T{turn:03} | Alive: {alive} | Captures: {captures}"
        if res.is_terminal:
            msg += f" | TERMINATED: {res.termination_reason}"
        
        self.lib.info(msg)

    def print_report(self, report):
        self.lib.info("=== FINAL REPORT ===")
        for k, v in report.items():
            if isinstance(v, float):
                self.lib.info(f"{k}: {v:.4f}")
            else:
                self.lib.info(f"{k}: {v}")
