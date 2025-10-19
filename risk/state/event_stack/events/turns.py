from ..stack import Event, Level
from ...territory import Territory

class PlacementPhase(Level):
    """
    An event representing the placement phase of a turn.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(
            f"Placement Phase - T{turn_number} - {player}"
        )

class TroopPlacementEvent(Event):
    """
    An event representing the placement of troops.
    """

    def __init__(self, 
        turn:int, player: str, territory: Territory, num_troops: int):
        super().__init__(
          f"Troop Placement-T{turn}-P{player}-R{territory}x{num_troops}",
          dict(
              territory=territory,
              num_troops=num_troops,
              turn=turn,
              player=player
          )
        )

    def __repr__(self) -> str:
        ret = f"TroopPlacementEvent({repr(self.context.turn)}, "
        ret += f"{repr(self.context.player)}, "
        ret += f"{repr(self.context.territory)}, "
        ret += f"{repr(self.context.num_troops)})"
        return ret
    
class PlacementPhaseEndEvent(Event):
    """
    A signal to the engines that the plan for the placement phase is
    complete.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(
            f"Placement Phase End - T{turn_number} - {player}", 
            dict(
                turn_number=turn_number,
                player=player
            )
        )

class AttackPhase(Level):
    """
    An event representing the attack phase of a turn.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(f"Attack Phase-T{turn_number}-P{player}")

class AttackOnTerritoryEvent(Event):
    """
    An event representing an attack on a territory.
    """

    def __init__(self, 
            player: str, turn_number:int, 
            from_territory: int, 
            to_territory: int, 
            attacking_troops: int):
        super().__init__(
            f"Attack-F{from_territory}-to-D{to_territory}-with-A{attacking_troops}",
            dict(
                from_territory=from_territory,
                to_territory=to_territory,
                attacking_troops=attacking_troops,
                turn_number=turn_number,
                player=player
            )
        )
        
class CasualtyEvent(Event):
    """
    An event representing casualties in an attack.
    """

    def __init__(self, 
        turn_number:int, territory: int, num_casualties: int):
        super().__init__(
            f"Casualties-in-T{territory}-L{num_casualties}-T{turn_number}",
            dict(
                territory = territory,
                num_casualties = num_casualties,
                turn_number=turn_number
            )
        )
    
class CaptureTerritoryEvent(Event):
    """
    An event representing the capture of a territory.
    """

    def __init__(self, 
        player: str, turn_number:int, 
        territory: int, conquered_from: int, 
        conquered_troops: int):
        super().__init__(
            f"Captured-C{territory}-from-F{conquered_from}-moving-" \
            + f"S{conquered_troops}",
            dict(
                player = player,
                turn_number = turn_number,
                territory = territory,
                conquered_from = conquered_from,
                conquered_troops = conquered_troops
            )
        )


class AttackPhaseEndEvent(Event):
    """
    A signal to the engines that the plan for the attack phase is
    complete.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(
            f"Attack Phase End-T{turn_number}-P{player}", 
            dict(
                turn_number=turn_number,
                player=player
            )
        )

class MovementPhase(Level):
    """
    An event representing the movement phase of a turn.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(
            f"Movement Phase-T{turn_number}-P{player}",
        )


class MovementOfTroopsEvent(Event):
    """
    An event representing the movement of troops.
    """

    def __init__(self, 
        player: str, turn_number:int, 
        from_territory: int, to_territory: int, 
        moving_troops: int):
        super().__init__(
            f"Movement of Troops-S{from_territory}-of-M{moving_troops}-to-E{to_territory}",
            dict(
                player = player,
                turn_number = turn_number,
                from_territory = from_territory,
                to_territory = to_territory,
                moving_troops = moving_troops,
            )
        )

class MovementPhaseEndEvent(Event):
    """
    A signal to the engines that the plan for the movement phase is
    complete.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(
            f"Attack Phase End-T{turn_number}-P{player}", 
            dict(
                turn_number=turn_number,
                player=player
            )
        )

