from ..stack import Event 

class PlacementPhaseEvent(Event):
    """
    An event representing the placement phase of a turn.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(f"Placement Phase - T{turn_number} - {player}")
        self.turn_number = turn_number
        self.player = player

class TroopPlacementEvent(Event):
    """
    An event representing the placement of troops.
    """

    def __init__(self, 
        turn:int, player: str, territory: str, num_troops: int):
        super().__init__(
          f"Troop Placement - T{turn} - {player} - {territory} x{num_troops}"
        )
        self.territory = territory
        self.num_troops = num_troops
        self.turn = turn
        self.player = player

    def __str__(self) -> str:
        ret = f"TroopPlacementEvent(territory={self.territory},"
        ret += f"num_troops={self.num_troops})"
        return ret

    def __repr__(self) -> str:
        ret = f"TroopPlacementEvent({repr(self.territory)},"
        ret += f"{repr(self.num_troops)})"
        return ret

class AttackPhaseEvent(Event):
    """
    An event representing the attack phase of a turn.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(f"Attack Phase - T{turn_number} - {player}")
        self.turn_number = turn_number
        self.player = player

    def __repr__(self):
        return f"AttackPhaseEvent(turn_number={self.turn_number}, player={repr(self.player)})"

class AttackOnTerritoryEvent(Event):
    """
    An event representing an attack on a territory.
    """

    def __init__(self, 
            player: str, turn_number:int, 
            from_territory: str, to_territory: str, attacking_troops: int):
        super().__init__(f"Attack on {to_territory} with {attacking_troops} - T{turn_number} - {player}")
        self.from_territory = from_territory
        self.to_territory = to_territory
        self.attacking_troops = attacking_troops
        self.turn_number = turn_number
        self.player = player

    def __repr__(self):
        return "".join([
                f"AttackOnTerritoryEvent(from_territory=",
                f"{repr(self.from_territory)}, ",
                f"to_territory={repr(self.to_territory)}, ",
                f"attacking_troops={self.attacking_troops}, ",
                f"turn_number={self.turn_number}, ",
                f"player={repr(self.player)})"
        ])
        
class CasualtyEvent(Event):
    """
    An event representing casualties in an attack.
    """

    def __init__(self, 
        player: str, turn_number:int, territory: str, num_casualties: int):
        super().__init__(f"Casualties in {territory} - T{turn_number} - {player}")
        self.territory = territory
        self.num_casualties = num_casualties
        self.turn_number = turn_number
        self.player = player

    def __repr__(self):
        return "".join([
                f"CasualtyEvent(territory={repr(self.territory)}, ",
                f"num_casualties={self.num_casualties}, ",
                f"turn_number={self.turn_number}, ",
                f"player={repr(self.player)})"
        ])
    
class CaptureTerritoryEvent(Event):
    """
    An event representing the capture of a territory.
    """

    def __init__(self, 
        player: str, turn_number:int, territory: str, conquered_from: str, conquered_troops: int):
        super().__init__(f"Capture of {territory} - T{turn_number} - {player}")
        self.territory = territory
        self.turn_number = turn_number
        self.player = player
        self.conquered_from = conquered_from
        self.conquered_troops = conquered_troops

    def __repr__(self):
        return "".join([
                f"CaptureTerritoryEvent(territory={repr(self.territory)}, ",
                f"turn_number={self.turn_number}, ",
                f"player={repr(self.player)}, ",
                f"conquered_from={repr(self.conquered_from)}, ",
                f"conquered_troops={self.conquered_troops})"
        ])

class MovementPhaseEvent(Event):
    """
    An event representing the movement phase of a turn.
    """

    def __init__(self, turn_number: int, player: str):
        super().__init__(f"Movement Phase - T{turn_number} - {player}")
        self.turn_number = turn_number
        self.player = player

class MovementOfTroopsEvent(Event):
    """
    An event representing the movement of troops.
    """

    def __init__(self, 
        player: str, turn_number:int, 
        from_territory: str, to_territory: str, moving_troops: int):
        super().__init__(f"Movement of Troops - T{turn_number} - {player}")
        self.from_territory = from_territory
        self.to_territory = to_territory
        self.moving_troops = moving_troops
        self.turn_number = turn_number
        self.player = player

    def __repr__(self):
        return "".join([
                f"MovementOfTroopsEvent(from_territory=",
                f"{repr(self.from_territory)}, ",
                f"to_territory={repr(self.to_territory)}, ",
                f"moving_troops={self.moving_troops}, ",
                f"turn_number={self.turn_number}, ",
                f"player={repr(self.player)})"
        ])