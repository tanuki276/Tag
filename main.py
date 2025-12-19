import sys
import yaml
import os
from pathlib import Path
from pkg.engine.core import SimulationCore
from pkg.factory.generator import WorldGenerator
from pkg.utils.logger import GameLogger
from pkg.analysis.evaluator import SimulationEvaluator
from pkg.utils.visualizer import MapVisualizer

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    try:
        config = load_config("config/settings/global_constants.yaml")
        learning_cfg = load_config("config/settings/learning.yaml")
    except FileNotFoundError:
        sys.exit(1)

    logger = GameLogger(level="INFO")
    
    grid_size = (config["world"]["width"], config["world"]["height"])
    viz = MapVisualizer(size=grid_size)

    generator = WorldGenerator(seed=config.get("seed"))
    world_state = generator.build_initial_state(config)

    core = SimulationCore(state=world_state, config=config, learning_cfg=learning_cfg)
    evaluator = SimulationEvaluator()

    viz.save_frame(0, core.get_snapshot())

    try:
        for turn in range(1, config["world"]["max_turns"] + 1):
            step_result = core.step()
            evaluator.record_step(step_result)
            logger.log_turn(turn, step_result)
            
            viz.save_frame(turn, step_result.snapshot)

            if step_result.is_terminal:
                break

    except Exception as e:
        logger.error(f"Engine Crash: {str(e)}")
        raise

    report = evaluator.generate_final_report()
    logger.print_report(report)

if __name__ == "__main__":
    main()
