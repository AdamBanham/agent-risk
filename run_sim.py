from risk.state.game_state import GameState
from risk.utils.loading import load_game_state_from_file
from risk.utils.replay import simulate_turns, SimulationConfiguration

import argparse


def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Starts and runs the simulation of risk from a " \
        "given state file, or from a new game. Only runs the engines, no UI.\n" \
        "Saves out both the stack and state as simulated_run.stack and " \
        "simulated_run.state respectively.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-s",
        "--state",
        type=str,
        default=False,
        help="Path to the state file to load (default: test.state)",
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

    parser.add_argument(
        "--configured",
        action="store_true",
        help="Use configured AI agents instead of default random agents.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    from risk.utils.logging import setLevel
    from logging import INFO
    setLevel(INFO)

    if not args.state:
        test_state = GameState.create_new_game(52, 8, 100)
        test_state.initialise()
    else:
        test_state = load_game_state_from_file(args.state)
        test_state.initialise(False)

    test_state.update_player_statistics()
    current_turn = test_state.current_turn

    new_state, tape, scorer = simulate_turns(
        test_state,
        args.turns,
        SimulationConfiguration(
            attack_rate=args.attack_rate,
            load_ai_from_file=args.configured,
            score=True
        ),
    )

    print("Simulation complete.")
    print(f"Final Turn: {new_state.current_turn}")

    recorder = tape
    state = new_state

    print("Final Scores:")
    for player_id, score in scorer.get_total_scores().items():
        print(f"Player {player_id}: {score} points")
    
    scorer.plot_scores()

    with open("simulated_run.stack", "w") as f:
        f.write(str(recorder.stack))
    with open("simulated_run.state", "w") as f:
        f.write(repr(state))
