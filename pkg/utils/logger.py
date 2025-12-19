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

    def info(self, msg): self.lib.info(msg)
    def error(self, msg): self.lib.error(msg)

    def log_turn(self, turn, res):
        alive = len([a for a in res.snapshot.values() if not a["is_oni"] and a["alive"] and not a["escaped"]])
        captures = len([a for a in res.actions.values() if a.status_update.get('alive') is False])
        msg = f"T{turn:03} | Alive: {alive} | Captures: {captures}"
        if res.is_terminal:
            msg += f" | {res.termination_reason}"
        self.lib.info(msg)

    def print_report(self, report):
        self.lib.info("=== FINAL REPORT ===")
        for k, v in report.items():
            self.lib.info(f"{k}: {v}")
