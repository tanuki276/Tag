import yaml

from pkg.engine.core import SimulationCore
from pkg.factory.generator import WorldGenerator


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build():
    config = load("config/settings/global_constants.yaml")
    learning = load("config/settings/learning.yaml")
    generation = load("config/settings/generation.yaml")
    config["world"]["seed"] = 1234
    state = WorldGenerator(seed=1234, generation_cfg=generation).build_initial_state(config)
    return config, learning, state


def test_smoke_runs_multiple_turns():
    config, learning, state = build()
    core = SimulationCore(state, config, learning)
    for _ in range(25):
        result = core.step()
        assert result.turn == state.turn
        assert result.snapshot
        if result.is_terminal:
            break


def test_identified_keys_open_exit():
    config, _, state = build()
    human = next(a for a in state.actor_data.values() if not a.is_oni)
    human.keys_identified = config["game_rules"]["num_keys_needed"]
    state._check_exit_condition()
    assert state.exit_open is True
