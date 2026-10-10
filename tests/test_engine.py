import numpy as np
import yaml

from pkg.engine.core import SimulationCore
from pkg.entities.humans.human_base import Human
from pkg.factory.generator import WorldGenerator
from pkg.schema.models import ActorStatus, LocalView


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


def test_escape_can_be_disabled():
    config, _, state = build()
    state.config["game_rules"]["escape_enabled"] = False
    human = next(a for a in state.actor_data.values() if not a.is_oni)
    human.keys_identified = config["game_rules"]["num_keys_needed"]
    state._check_exit_condition()
    assert state.exit_open is False


def test_human_commits_to_open_exit_when_close_even_if_oni_visible():
    config, _, _ = build()
    grid = np.zeros((7, 7), dtype=int)
    human = Human("H_TEST", (3, 3), config)
    view = LocalView(
        pos=(3, 3),
        actors=[
            ActorStatus(
                a_id="O_TEST",
                pos=(3, 5),
                is_oni=True,
                alive=True,
                escaped=False,
                role="CHASER",
                job=None,
                stamina=None,
            )
        ],
        elements=[],
        memory={
            "grid_map": grid,
            "exit_open": True,
            "exit_pos": (3, 4),
            "current_turn": 10,
        },
    )
    intent = human.decide(view)
    assert tuple(intent.target_pos) == (3, 4)
    assert intent.metadata.get("mode") == "exit_commit"
