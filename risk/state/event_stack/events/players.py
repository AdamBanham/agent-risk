
from ..events import Event 
from ...game_state import GameState
from .sideffects import SideEffectEvent

class TerritorySelectedEvent(Event):
    """
    Event triggered when a player selects a territory.
    """

    def __init__(self, territory_id: int):
        super().__init__(
            "Territory Selected Event",
            dict(
                territory_id=territory_id
            )
        )

class ChangeSelectedTerritoryEvent(SideEffectEvent):
    """
    Side effect event to change the currently selected territory.
    """

    def __init__(self, territory_id: int, previous_territory_id: int):
        super().__init__(
            "Changing selected territory",
            dict(
                previous_territory_id=previous_territory_id,
                new_territory_id=territory_id
            )
        )

    def apply(self, state: GameState) -> None:
        state.ui_state.selected_territory_id = self.context.new_territory_id

    def revert(self, state: GameState) -> None:
        state.ui_state.selected_territory_id = self.context.previous_territory_id

class TriggerAttackPopupEvent(Event):
    """
    Event to trigger the attack popup for a selected territory.
    """

    def __init__(self, attacker_id: int, defender_id: int):
        super().__init__(
            "Trigger Attack Popup Event",
            dict(
                attacker_id=attacker_id,
                defender_id=defender_id
            )
        )