"""
This module contains the logic for producing a side effect
on the world state or a presumed world state.
"""

from ..events import Event
from ...game_state import GameState
from abc import ABC 

class SideEffect(ABC):
    """
    The behaviour contract of a side effect within the simulation framework.
    Side effects are responsible for applying changes to the world state
    based on certain triggers or conditions.

    .. required-methods ::
        - apply:
            `apply(state: GameState) -> None`
        - revert:
            `revert(state: GameState) -> None`

    """

    def apply(self, state: 'GameState') -> None:
        """
        Apply the side effect to the given game state.

        :param state:
          `GameState`
          The game state to which the side effect will be applied.
        """
        pass

    def revert(self, state: 'GameState') -> None:
        """
        Revert the side effect from the given game state.

        :param state:
          `GameState`
          The game state from which the side effect will be reverted.
        """
        pass 
            

class SideEffectEvent(Event):
    """
    An event that produces a side effect on the world state.

    .. attributes ::
       - description:
            `str`
            A description of the side effect.

    """

    def __init__(self, description: str):
        super().__init__("SideEffectEvent")