from risk.state import GameState
from risk.agents import create_ai_game
from risk.utils.loading import load_game_state_from_file

import argparse

def parse_args():

    parser = argparse.ArgumentParser(
        description="Run a simulation from a saved test game state." \
        "Ensures that player one is a human player, and all other players are AI agents." \
        "Setting --player will set that player as the human player.",
    )

    parser.add_argument(
        "--state-file",
        type=str,
        default="test.state",
        help="Path to the saved game state file.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )

    parser.add_argument(
        "--player",
        type=int,
        default=0,
        help="ID of the human player (default: 1).",
    )

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    if args.debug:
        from risk.utils.logging import setLevel 
        from logging import DEBUG
        setLevel(DEBUG)

    test_state = load_game_state_from_file(args.state_file)
    test_state.initialise(False)
    test_state.update_player_statistics()

    if args.player >= test_state.num_players or args.player < 0:
        raise ValueError(f"Player ID {args.player} is out of range for this game.")

    game_loop = create_ai_game(
        ai_player_ids=[
            player.id for player in test_state.players.values() if player.id != args.player
        ],
        play_from_state=test_state,
    )
    game_loop.initialize()
    game_loop.run()
