from risk.state.game_state import GameState

def copy_game_state(game_state: GameState) -> GameState:
    """
    Creates a deep copy of the given GameState by using its string representation.
    This method ensures that all nested objects are also copied.

    :param game_state: The GameState instance to copy.
    :returns: A new GameState instance that is a deep copy of the original.
    """
    # import needed classes for the repr to work
    from risk.state.game_state import GameState, Player, Territory, GamePhase
    from risk.state.territory import TerritoryState
    from risk.utils.map import Graph, Node, Edge
    state:GameState = eval(repr(game_state))
    state.initialise(False)
    state.update_player_statistics()
    return state