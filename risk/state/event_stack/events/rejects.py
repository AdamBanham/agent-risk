
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

class RejectTransfer(Rejected):
    """
    An event representing the rejection of a troop transfer action.
    """

    def __init__(self,
        turn_number:int, player: str,
        from_territory: int,
        to_territory: int,
        num_troops: int,
        reason: str):
        super().__init__(
            f"Reject-Transfer-T{turn_number}-P{player}-FT{from_territory}-TT{to_territory}-U{num_troops}: {reason}",
            dict(
                turn_number=turn_number,
                player=player,
                from_territory=from_territory,
                to_territory=to_territory,
                num_troops=num_troops,
                reason=reason
            )
        )