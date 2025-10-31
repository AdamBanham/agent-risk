import sys
from risk.game.loop import GameLoop
from risk.agents import create_ai_game
from risk.state.game_state import GameState, Player, Territory, GamePhase
from risk.state.territory import TerritoryState
from os.path import join

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
        "--player",
        type=int,
        default=-1,
        help="ID of the player to control (default: -1, meaning all AI players)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    print("Loading state from file:", args.state)
    test_state: GameState = eval(open(join(".", args.state), "r").read())
    test_state.initialise(False)
    if args.player != -1:
        # Set all other players to inactive
        ai_players = [
            player.id
            for player in test_state.players.values()
            if player.id != args.player
        ]
    else:
        ai_players = [player.id for player in test_state.players.values()]
    game_loop = create_ai_game(
        ai_player_ids=ai_players,
        play_from_state=test_state,
        ai_delay=args.ai_delay,
        attack_probability=args.attack_rate,
        sim_delay=args.sim_delay,
    )
    game_loop.initialize()

    try:
        game_loop.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error running simulation: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        print("Simulation ended.")

        recorder = game_loop.sim_controller.tape
        state = game_loop.sim_controller.game_state

        with open("simulation_from.stack", "w") as f:
            f.write(str(recorder.stack))
        with open("simulation_from.state", "w") as f:
            f.write(repr(state))
