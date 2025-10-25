from risk.game.loop import GameLoop
from risk.agents import create_ai_game
from risk.state.game_state import GameState, Player,  GamePhase
from risk.state.territory import Territory, TerritoryState

if __name__ == "__main__":

    test_state: GameState = eval(open("test.state", "r").read())
    test_state.initialise()
    game_loop = create_ai_game(
        ai_player_ids=[
            player.id for player in test_state.players.values() if player.id != 0
        ],
        play_from_state=test_state,
    )
    game_loop.initialize()
    game_loop.run()
