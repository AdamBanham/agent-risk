"""
This module is for loading game states from files.
"""
from risk.state.game_state import GameState

def load_game_state_from_file(file_path: str) -> GameState:
    """
    Load a game state from a specified file.

    :param file_path: Path to the file containing the game state
    :returns: The loaded game state object
    """
    from risk.state.game_state import GameState, Player, Territory, GamePhase
    from risk.state.territory import TerritoryState
    from risk.utils.map import Graph, Node, Edge
    
    with open(file_path, "r") as file:
        state_data = file.read()
    game_state = eval(state_data)
    return game_state
