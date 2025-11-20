from risk.state.game_state import GameState, Player, Territory, GamePhase
from risk.state.territory import TerritoryState
from risk.utils.replay import simulate_turns, SimulationConfiguration
from risk.utils.logging import info, debug

import argparse

import math


def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Run the Agent Risk pygame simulation with AI agents from a known state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--ai-delay",
        type=float,
        default=0.1,
        help="Delay between AI actions in seconds (default: 0.1)",
    )

    parser.add_argument(
        "--attack-rate",
        type=float,
        default=0.85,
        help="AI attack probability 0.0-1.0 (default: 0.85)",
    )

    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of turns to simulate forward (default: 10)",
    )

    return parser.parse_args()


def create_options():
    """
    For each known ai family, find and return the configuration options.
    """

    from risk.agents.finder import AgentTypes, AgentStrategies

    options = {}
    for atype in AgentTypes.__members__.values():
        name = atype.value[0]
        family = atype.value[1]

        options[name] = []
        for strat in AgentStrategies.__members__.values():
            strategy_name = strat.value
            try:
                family.get_agent(strat)
                options[name].append(strategy_name)
            except Exception as e:
                print(
                    f"Could not get agent for {name} with strategy {strategy_name}: {e}"
                )

    return options


def convert_option_to_config(families, selections) -> dict:
    """
    Given a list of options, convert to configuration dict.
    """

    config = {}
    for player_id, (family, select) in enumerate(zip(families, selections)):
        config[player_id] = {
            "type": family,
            "strat": select,
        }
    return json.loads(json.dumps(config, indent=4))


def config_name(config, player_id):
    """Generate a name for the given player configuration."""
    return f"player{player_id}-{config[player_id]['type']}-{config[player_id]['strat']}"


if __name__ == "__main__":
    args = parse_arguments()

    import random
    import json
    from risk.utils.logging import setLevel
    from os.path import exists, join
    from os import mkdir
    from itertools import product
    from logging import INFO
    from time import time

    setLevel(INFO)

    options = create_options()
    info("Available AI Agent Options:")
    info(options)
    players = len(options.keys())

    combos = list(product(*list(options.values())))
    info(f"Total combinations to check: {len(combos)}")
    info("Sample combinations:")
    for _ in range(min(10, len(combos))):
        combo = random.choice(combos)
        info(f"Sample :: {combo}")
        assert len(combo) == players

    config = convert_option_to_config(options.keys(), combos[0])
    info("Sample configuration:")
    info(config)

    eval_folder = "eval_runs_{id:04d}"
    run_id = 0
    while exists(join(".", "eval", eval_folder.format(id=run_id))):
        run_id += 1
    eval_path = join(".", "eval", eval_folder.format(id=run_id))
    mkdir(eval_path)
    info(f"Creating evaluation run folder at: {eval_path}")

    starting_state = GameState.create_new_game(200, players, 200)
    starting_state.initialise()

    all_runs_start = time()
    runs = []
    summary_stats = dict(
        (
            family,
            dict(
                (strategy, {"runtime": [], "score": []})
                for strategy in options[family]
            ),
        )
        for family in options.keys()
    )

    for id, combo in enumerate(combos):

        config = convert_option_to_config(options.keys(), combo)
        info(f"Running simulation with configuration: {config}")

        combo_start = time()
        new_state, tape, scorer = simulate_turns(
            starting_state,
            args.turns,
            SimulationConfiguration(
                attack_rate=args.attack_rate,
                load_ai_from_file=True,
                configuration=config,
                score=True,
            ),
        )
        combo_end = time() - combo_start
        info(f"Completed simulation in {combo_end:.2f} seconds.")
        info(f"Final Turn: {new_state.current_turn}")

        recorder = tape
        state = new_state
        results = {}
        scores = scorer.get_total_scores(False)

        info("Final Scores:")
        for player_id, (family, strat) in enumerate(zip(options.keys(), combo)):
            score = scores[player_id]
            runtime = state.players[player_id].runtime
            info(
                f"Player {player_id}: {score} points with a runtime of {runtime:.2f} seconds"
            )
            results[config_name(config, str(player_id))] = {
                "score": score,
                "runtime": runtime,
            }
            summary_stats[family][strat]["score"].append(score)
            summary_stats[family][strat]["runtime"].append(runtime)
        results["total_time"] = combo_end
        runs.append(combo_end)

        with open(join(eval_path, f"combo_{id:04d}.stack"), "w") as f:
            f.write(str(recorder.stack))
        with open(join(eval_path, f"combo_{id:04d}.state"), "w") as f:
            f.write(repr(state))
        with open(join(eval_path, f"combo_{id:04d}.config"), "w") as f:
            f.write(json.dumps(config, indent=4))
        with open(join(eval_path, f"combo_{id:04d}.scores"), "w") as f:
            f.write(json.dumps(results, indent=4))

    all_runs_end = time() - all_runs_start
    info(f"Completed all {len(combos)} simulations in {all_runs_end:.2f} seconds.")
    info(f"Average time per simulation: {all_runs_end / len(combos):.2f} seconds.")

    condensed_stats = {}
    for family in summary_stats.keys():
        condensed_stats[family] = {}
        for strat in summary_stats[family].keys():
            runtimes = summary_stats[family][strat]["runtime"]
            r_mean = sum(runtimes) / len(runtimes)
            r_var = sum((x - r_mean) ** 2 for x in runtimes) / len(runtimes)
            scores = summary_stats[family][strat]["score"]
            s_mean = sum(scores) / len(scores)
            s_var = sum((x - s_mean) ** 2 for x in scores)
            condensed_stats[family][strat] = {
                "std_runtime": math.sqrt(r_var),
                "avg_runtime": r_mean,
                "std_score": math.sqrt(s_var),
                "avg_score": s_mean,
            }

    with open(join(eval_path, "summary.json"), "w") as f:
        summary = {
            "total_simulations": len(combos),
            "total_time": all_runs_end,
            "average_time": all_runs_end / len(combos),
            "individual_times": runs,
            "detailed_stats": condensed_stats,
        }
        f.write(json.dumps(summary, indent=4))
