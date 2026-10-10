import sys

import yaml

from pkg.analysis.evaluator import SimulationEvaluator
from pkg.engine.core import SimulationCore
from pkg.factory.generator import WorldGenerator
from pkg.utils.logger import GameLogger
from pkg.utils.visualizer import URLMapVisualizer


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main():
    try:
        config = load_config("config/settings/global_constants.yaml")
        learning_cfg = load_config("config/settings/learning.yaml")
        generation_cfg = load_config("config/settings/generation.yaml")
    except FileNotFoundError as exc:
        print(f"Missing configuration: {exc}", file=sys.stderr)
        return 1

    logger = GameLogger(level="INFO")
    visualizer = URLMapVisualizer(asset_urls=config.get("assets", {}), output_dir="frames")
    generator = WorldGenerator(
        seed=config["world"].get("seed"),
        generation_cfg=generation_cfg,
    )
    world_state = generator.build_initial_state(config)
    core = SimulationCore(world_state, config, learning_cfg)
    evaluator = SimulationEvaluator()

    visualizer.save_frame(
        0,
        core.get_snapshot(),
        world_state.grid,
        world_state.exit_pos,
        grid_items=world_state.grid_items,
        exit_open=world_state.exit_open,
    )

    try:
        for turn in range(1, config["world"]["max_turns"] + 1):
            result = core.step()
            evaluator.record_step(result)
            logger.log_turn(turn, result)
            visualizer.save_frame(
                turn,
                result.snapshot,
                world_state.grid,
                world_state.exit_pos,
                grid_items=world_state.grid_items,
                exit_open=world_state.exit_open,
            )
            if result.is_terminal:
                break
    except Exception as exc:
        logger.lib.error(f"Engine Crash: {exc}")
        raise

    logger.print_report(evaluator.generate_final_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
