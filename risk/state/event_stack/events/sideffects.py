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
            territory.add_armies(self.context.num_armies)
            state.placements_left -= self.context.num_armies

    def revert(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)

        if territory:
            territory.remove_armies(self.context.num_armies)
        state.placements_left += self.context.num_armies

class TransferArmies(SideEffectEvent):
    """
    A side effect that transfers armies from one territory to another.

    .. attributes ::
        - context.from_territory_id
        - context.to_territory_id
        - context.num_armies
    """

    def __init__(self, from_territory_id: str, to_territory_id: str, num_armies: int):
        super().__init__(
            f"Transfer Armies: Move {num_armies} armies from {from_territory_id} to {to_territory_id}",
            dict(
                from_territory_id=from_territory_id,
                to_territory_id=to_territory_id,
                num_armies=num_armies
            )
        )

    def apply(self, state: 'GameState') -> None:
        from_territory = state.get_territory(self.context.from_territory_id)
        to_territory = state.get_territory(self.context.to_territory_id)

        if from_territory and to_territory:
            from_territory.remove_armies(self.context.num_armies)
            to_territory.add_armies(self.context.num_armies)

    def revert(self, state: 'GameState') -> None:
        from_territory = state.get_territory(self.context.from_territory_id)
        to_territory = state.get_territory(self.context.to_territory_id)

        if from_territory and to_territory:
            from_territory.add_armies(self.context.num_armies)
            to_territory.remove_armies(self.context.num_armies)


class CaptureTerritory(SideEffectEvent):
    """
    A side effect that changes the ownership of a territory.

    .. attributes ::
        - context.territory_id
        - context.new_owner_id
        - context.previous_owner_id
    """

    def __init__(self, territory_id: str, new_owner_id: int, previous_owner_id: int):
        super().__init__(
            f"Capture Territory: {territory_id} by {new_owner_id}",
            dict(
                territory_id=territory_id,
                new_owner_id=new_owner_id,
                previous_owner_id=previous_owner_id
            )
        )

    def apply(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.set_owner(self.context.new_owner_id)
            territory.armies = 0
        state.update_player_statistics()

    def revert(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.set_owner(self.context.previous_owner_id)
            territory.armies = 0
        state.update_player_statistics()

class CasualitiesOnTerritory(SideEffectEvent):
    """
    A side effect that removes armies from a territory due to casualties.

    .. attributes ::
        - context.territory_id
        - context.num_casualties
    """

    def __init__(self, territory_id: str, num_casualties: int):
        super().__init__(
            f"Casualties on Territory: Remove {num_casualties} armies from territory {territory_id}",
            dict(
                territory_id=territory_id,
                num_casualties=num_casualties
            )
        )

    def apply(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.remove_armies(self.context.num_casualties)

        if territory.armies < 1:
            return [
                ClearTerritory(
                    territory.id,
                    territory.owner
                )
            ]
        
        state.update_player_statistics()

    def revert(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)

        if territory:
            territory.add_armies(self.context.num_casualties)

        state.update_player_statistics()

class ClearTerritory(SideEffectEvent):
    """
    A side effect that clears the owner of a territory.
    
    .. attributes ::
        - context.territory_id
        - context.previous_owner_id
    """

    def __init__(self, territory_id: str, previous_owner_id: int):
        super().__init__(
            f"Clear Territory: {territory_id}",
            dict(
                territory_id=territory_id,
                previous_owner_id=previous_owner_id
            )
        )
    
    def apply(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.set_owner(None)
        state.update_player_statistics()

    def revert(self, state: 'GameState') -> None:
        territory = state.get_territory(self.context.territory_id)
        if territory:
            territory.set_owner(self.context.previous_owner_id)
        state.update_player_statistics()
