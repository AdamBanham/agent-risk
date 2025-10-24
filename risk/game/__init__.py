"""
This module contains all the game loop and event handling logic for the Risk 
simulation.
It manages the main event loop, user inputs, and rendering using pygame.
"""

from .loop import GameLoop, main
from .renderer import GameRenderer
from .input import InputHandler, GameInputHandler
from .selection import TerritorySelectionHandler
from ..state.ui import TurnUI, UIAction
from .ui_renderer import UIRenderer
from .animation import AnimationManager, ArrowAnimation, CrossAnimation, TickAnimation, RandomWalkAnimation

__all__ = ['GameLoop', 'GameRenderer', 'InputHandler', 'GameInputHandler', 
           'TerritorySelectionHandler', 'TurnUI', 'UIAction', 'UIRenderer', 
           'AnimationManager', 'ArrowAnimation', 'CrossAnimation', 'TickAnimation', 'RandomWalkAnimation', 'main']