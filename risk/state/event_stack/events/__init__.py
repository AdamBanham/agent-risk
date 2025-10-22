"""
A module for the types of the events possible on the 
event stack of the simulation.
"""

from ...event_stack import Event

class GameEvent(Event):
    """
    The starting event for all simulations to trigger 
    the game loop.
    """
    
    def __init__(self):
        super().__init__("Game")

from .turns import *
from .sideffects import *
from .rejects import *
from .fights import *