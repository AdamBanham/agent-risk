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

    .. required-methods ::
        - apply:
            `apply(state: GameState) -> None`
        - revert:
            `revert(state: GameState) -> None`
    """

    def __str__(self):
        return f"SideEffect: {self.name}, Context: {str(self.context)}"

class UpdateReinforcements(SideEffectEvent):
    """
    A side effect that setups up the number of reinforcements
    for the placement phase.

    .. attributes ::
        - player_id
    """

    def __init__(self, player_id:int):
        super().__init__(
            f"Setup reinforcements for player {player_id}",
            dict(
                player_id=player_id
            )
        )

    def apply(self, state: GameState) -> None:
        reinforcements = state.calculate_reinforcements(
            self.context.player_id
        )
        state.placements_left = reinforcements

    def revert(self, state: GameState) -> None:
        state.placements_left = 0
        
class ClearReinforcements(SideEffectEvent):
    """
    Clears any remaining reinforcements.

    .. attributes:
        - context.remaining
    """

    def __init__(self, remaining:int):
        super().__init__(
            "Clear reinforcements.",
            dict(
                remaining=remaining
            )
        )

    def apply(self, state):
        state.placements_left = 0 

    def revert(self, state):
        state.placements_left = self.context.remaining

class AdjustArmies(SideEffectEvent):
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
            f"Adjust Armies: Add {num_armies} armies to territory {territory_id}",
            dict(
                territory_id=territory_id,
                num_armies=num_armies
            )
        )

    def apply(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.armies += self.context.num_armies
            state.placements_left -= self.context.num_armies

    def revert(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)

        if territory:
            territory.armies -= self.context.num_armies

class CaptureTerritory(SideEffectEvent):
    pass

class CasualitiesOnTerritory(SideEffectEvent):
    pass 

class ClearTerritory(SideEffectEvent):
    pass
