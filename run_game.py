"""
Simple script to run the Agent Risk pygame simulation with AI agents.

Usage:
    python run_game.py [-g REGIONS] [-p PLAYERS] [-s ARMY_SIZE] [--attack-rate RATE] [--ai-delay DELAY] [--human-player ID]

Arguments:
    -g, --regions        Number of territories/regions to generate (default: 27)
    -p, --players        Number of players in the simulation (default: 3)
    -s, --army-size      Starting army size per player (default: 20)
    --attack-rate        AI attack probability 0.0-1.0 (default: 0.85)
    --ai-delay           Delay between AI actions in seconds (default: 1.0)
    --human-player       Player ID to be human (0 to players-1), others will be AI (default: all AI)
"""

import sys
import os
import argparse

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from risk.agents import create_ai_game
from risk.engine.risk import RiskPlayerScoresEngine


def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Run the Agent Risk pygame simulation with AI agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-g",
        "--regions",
        type=int,
        default=42,
        help="Number of territories/regions to generate (default: 42)",
    )

    parser.add_argument(
        "-p",
        "--players",
        type=int,
        default=5,
        help="Number of players in the simulation (default: 5)",
    )

    parser.add_argument(
        "-s",
        "--army-size",
        type=int,
        default=52,
        help="Starting army size per player (default: 52)",
    )

    parser.add_argument(
        "--attack-rate",
        type=float,
        default=0.85,
        help="AI attack probability 0.0-1.0 (default: 0.85)",
    )

    parser.add_argument(
        "--ai-delay",
        type=float,
        default=0.05,
        help="Delay between AI actions in seconds (default: 0.05)",
    )

    parser.add_argument(
        "--human-player",
        type=int,
        default=None,
        help="Player ID to be human (0 to players-1), all others will be AI. If not specified, all players are AI.",
    )

    parser.add_argument(
        "--sim-delay",
        type=float,
        default=0.1,
        help="Delay between simulation steps in seconds (default: 0.1)",
    )

    parser.add_argument(
        "--sim-speed",
        type=int,
        default=120,
        help="Simulation batch size between steps (default: 120)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging",
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Enable info mode with standard logging",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    from risk.utils.logging import setLevel
    from logging import DEBUG, INFO

    if args.info:
        setLevel(INFO)
    elif args.debug:
        setLevel(DEBUG)

    # Validate arguments
    if args.regions < 1:
        print("Error: Number of regions must be at least 1", file=sys.stderr)
        sys.exit(1)

    if args.players < 2:
        print("Error: Number of players must be at least 2", file=sys.stderr)
        sys.exit(1)

    if args.army_size < 1:
        print("Error: Army size must be at least 1", file=sys.stderr)
        sys.exit(1)

    if not (0.0 <= args.attack_rate <= 1.0):
        print("Error: Attack rate must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    if args.human_player is not None:
        if args.human_player < 0 or args.human_player >= args.players:
            print(
                f"Error: Human player ID must be between 0 and {args.players-1}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Determine which players are AI
    if args.human_player is not None:
        # All players except the specified one are AI
        ai_player_ids = [i for i in range(args.players) if i != args.human_player]
        human_player_id = args.human_player
        game_mode = f"{len(ai_player_ids)} AI vs 1 Human"
    else:
        # All players are AI
        ai_player_ids = list(range(args.players))
        human_player_id = None
        game_mode = "All AI"

    print(f"Starting Agent Risk simulation:")
    print(f"  Regions: {args.regions}")
    print(f"  Players: {args.players} ({game_mode})")
    print(f"  Armies per player: {args.army_size}")
    if ai_player_ids:
        print(f"  AI players: {ai_player_ids}")
        print(f"  AI attack rate: {args.attack_rate:.1%}")
        print(f"  AI turn delay: {args.ai_delay}s")
    if human_player_id is not None:
        print(f"  Human player: {human_player_id}")
    print()
    print("Controls:")
    if human_player_id is not None:
        print("  - Use UI buttons and territory clicks for your turn")
        print("  - AI players will take turns automatically")
    else:
        print("  - Watch AI agents play automatically")
    print("  - Ctrl+R: Regenerate board")
    print("  - Ctrl+G: Increase regions (+1)")
    print("  - Ctrl+P: Increase players (+1)")
    print("  - Ctrl+S: Increase armies (+1)")
    print("  - H: Show help")
    print("  - ESC: Quit")
    print()

    # Create AI game with specified AI players
    try:
        game = create_ai_game(
            regions=args.regions,
            num_players=args.players,
            starting_armies=args.army_size,
            ai_player_ids=ai_player_ids,
            attack_probability=args.attack_rate,
            ai_delay=args.ai_delay,
            sim_delay=args.sim_delay,
            sim_speed=args.sim_speed,
        )

        if human_player_id is not None:
            print(
                f"Game created successfully. Player {human_player_id} is human, others are AI agents..."
            )
        else:
            print("Game created successfully. All players are AI agents...")

        scorer = RiskPlayerScoresEngine(args.players)
        game.sim_controller.add_engine(scorer)
        game.run()

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error running simulation: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        print("Simulation ended.")

        recorder = game.sim_controller.tape
        state = game.sim_controller.game_state

        with open("simulation.stack", "w") as f:
            f.write(str(recorder.stack))
        with open("simulation.state", "w") as f:
            f.write(repr(state))

        scores = scorer.get_total_scores(False)
        print("Final Player Scores:")
        for player in range(args.players):
            print(
                (f"  Player {player}: Cum. Score = "
                 f"{scores.get(player, 0.0):.2f}, "
                 f"Runtime = {state.players[player].runtime:.2f}s")
            )

        scorer.plot_scores()
