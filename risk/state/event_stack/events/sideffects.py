"""
This module contains the logic for producing a side effect
on the world state or a presumed world state.
"""

from ..events import Event
from ...game_state import GameState
from abc import ABC, abstractmethod

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

    @abstractmethod
    def apply(self, state: 'GameState') -> None:
        """
        Apply the side effect to the given game state.

        :param state:
          `GameState`
          The game state to which the side effect will be applied.
        """
        pass

    @abstractmethod
    def revert(self, state: 'GameState') -> None:
        """
        Revert the side effect from the given game state.

        :param state:
          `GameState`
          The game state from which the side effect will be reverted.
        """
        pass 
            

class SideEffectEvent(Event, SideEffect):
    """
    An event that produces a side effect on the world state.

    .. attributes ::
       - description:
            `str`
            A description of the side effect.

    """

    def __init__(self, description: str):
        super().__init__("SideEffectEvent")


class AddArmiesSE(Event, SideEffect):
    """
    A side effect that adds armies to a territory.

    .. attributes ::
       - territory_id:
            `str`
            The ID of the territory to which armies will be added.
       - num_armies:
            `int`
            The number of armies to add.

    """

    def __init__(self, territory_id: str, num_armies: int):
        super().__init__(
            f"Add {num_armies} armies to territory {territory_id}",
            dict(
                territory_id=territory_id,
                num_armies=num_armies
            )
        )

    def apply(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.armies += self.context.num_armies

    def revert(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)

        if territory:
            territory.armies -= self.context.num_armies
