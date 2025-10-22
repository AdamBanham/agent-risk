
from ..events import Event
from abc import ABC

class Rejected(Event, ABC):
    """
    An abstract event representing a rejected action within the simulation.
    """


class RejectTroopPlacement(Rejected):
    """
    An event representing the rejection of a troop placement.
    """

    def __init__(self, 
        turn_number:int, player: str, 
        territory: int, num_troops: int, 
        reason: str):
        super().__init__(
            f"Reject-Troop-Placement-T{territory}-L{num_troops}-T{turn_number}: {reason}",
            dict(
                territory = territory,
                num_troops = num_troops,
                turn_number=turn_number,
                player=player,
                reason=reason
            )
        )

class RejectAttack(Rejected):
    """
    An event representing the rejection of an attack action.
    """

    def __init__(self,
        turn_number:int, player: str,
        attacking_territory: int,
        defending_territory: int,
        reason: str):
        super().__init__(
            f"Reject-Attack-T{turn_number}-P{player}-AT{attacking_territory}-DT{defending_territory}: {reason}",
            dict(
                turn_number=turn_number,
                player=player,
                attacking_territory=attacking_territory,
                defending_territory=defending_territory,
                reason=reason
            )
        )