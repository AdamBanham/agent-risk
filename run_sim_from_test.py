from risk.game.loop import GameLoop, GamePhase
from risk.agents import create_ai_game
from risk.state.game_state import GameState, Player, Territory, TerritoryState

if __name__ == "__main__":

    test_state: GameState = eval(open("test.state", "r").read())
    test_state.set_adjacent_territories()
    game_loop = create_ai_game(
        ai_player_ids=[player.id for player in test_state.players.values() if player.id != 0],
        play_from_state=test_state,
    )
    game_loop.initialize()
    game_loop.run()