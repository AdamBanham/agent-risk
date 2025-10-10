"""
This module contains all the game loop and event handling logic for the Risk 
simulation.
It manages the main event loop, user inputs, and rendering using pygame.
"""

from .loop import GameLoop, main
from .renderer import GameRenderer
from .input import InputHandler, GameInputHandler
from .selection import TerritorySelectionHandler

__all__ = ['GameLoop', 'GameRenderer', 'InputHandler', 'GameInputHandler', 'TerritorySelectionHandler', 'main']