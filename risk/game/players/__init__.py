from .engine import *


def add_player_engines(controller, turn_manager):
    """
    Adds player engines to the game loop for handling human player actions.

    :param game_loop: The main game loop instance
    """

    # Add Player Engine
    controller.add_engine(PlayerEngine("Player Engine"))
    controller.add_engine(PlayerPlacementEngine())
    controller.add_engine(PlayerAttackEngine())
    controller.add_engine(UITriggersEngine())
    controller.add_engine(PlayerMovementEngine())
