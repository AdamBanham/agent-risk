from risk.state.game_state import GameState, Player, Territory, GamePhase
from risk.state.territory import TerritoryState
from risk.utils.replay import simulate_turns, SimulationConfiguration

import argparse


def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Run the Agent Risk pygame simulation with AI agents from a known state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-s",
        "--state",
        type=str,
        default="test.state",
        help="Path to the state file to load (default: test.state)",
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
        "--sim-delay",
        type=float,
        default=0.2,
        help="Delay between simulation steps in seconds (default: 0.2)",
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

    test_state: GameState = eval(open(args.state, "r").read())
    test_state.initialise(False)

    current_turn = test_state.current_turn

    new_state, tape = simulate_turns(
        test_state,
        args.turns,
        SimulationConfiguration(
            attack_rate=args.attack_rate,
            load_ai_from_file=args.configured,
        ),
    )

    print("Simulation complete.")
    print(f"Loaded state from {args.state}, starting from turn {current_turn}.")
    print(f"Final Turn: {new_state.current_turn}")

    recorder = tape
    state = new_state

    with open("simulation_forward.stack", "w") as f:
        f.write(str(recorder.stack))
    with open("simulation_forward.state", "w") as f:
        f.write(repr(state))
