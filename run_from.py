from risk.game.loop import GameLoop, GamePhase
from risk.agents import create_ai_game
from risk.state.game_state import GameState, Player, Territory, TerritoryState

import argparse

def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Run the Agent Risk pygame simulation with AI agents from a known state.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-s', '--state',
        type=str,
        default="test.state",
        help='Path to the state file to load (default: test.state)'
    )

    parser.add_argument(
        '--ai-delay',
        type=float,
        default=1,
        help='Delay between AI actions in seconds (default: 1.0)'
    )

    parser.add_argument(
        '--attack-rate',
        type=float,
        default=0.85,
        help='AI attack probability 0.0-1.0 (default: 0.85)'
    )

    parser.add_argument(
        '--sim-delay',
        type=float,
        default=1.0,
        help='Delay between simulation steps in seconds (default: 1.0)'
    )

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    test_state: GameState = eval(open(args.state, "r").read())
    test_state.set_adjacent_territories()
    game_loop = create_ai_game(
        ai_player_ids=[player.id for player in test_state.players.values() if player.id != 0],
        play_from_state=test_state,
        ai_delay=args.ai_delay,
        attack_probability=args.attack_rate,
        sim_delay=args.sim_delay,
    )
    game_loop.initialize()
    game_loop.run()