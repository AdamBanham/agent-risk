"""
This module contains fight-related events for the event stack.
"""

from ..events import Event
from ...fight import Fight, FightResult

class FightEvent(Event):
    """
    An event that triggers the response to resolve a fight
    between attacking troops on a territory with defending troops.

    .. attributes ::
        - conttext.attacking_territory_id
        - context.defending_territory_id
        - context.attacking_armies
        - context.defending_armies
        - context.player_id
        - context.turn
    """

    def __init__(self, 
        attacking_territory_id: int,
        defending_territory_id: int,
        attacking_armies: int,
        defending_armies: int,
        player_id: int,
        turn: int,         
        ):
        super().__init__(
            f"FightEvent on T{turn}-P{player_id}: {attacking_territory_id} vs {defending_territory_id}",
            dict(
                attacking_territory_id=attacking_territory_id,
                defending_territory_id=defending_territory_id,
                attacking_armies=attacking_armies,
                defending_armies=defending_armies,
                player_id=player_id,
                turn=turn
            )
        )
    

class ResolveFightEvent(FightEvent):
    """
    An event recording the resolution of a fight between attacking
    and defending troops on a territory.

    .. attributes ::
        - context.attacking_territory_id 
        - context.defending_territory_id
        - context.surviving_attacking_armies
        - context.surviving_defending_armies
        - context.fight
        - context.fight_result
        - context.player_id
        - context.turn

    """
    def __init__(self,
            attacking_territory_id: int,
            defending_territory_id: int,
            surviving_attacking_armies: int,
            surviving_defending_armies: int,
            fight: Fight,
            fight_result: FightResult,
            player_id: int,
            turn: int,
        ):
        super().__init__(
           f"FightResolved on T{turn}-P{player_id}: {str(fight_result)}",
            dict(
            attacking_territory_id=attacking_territory_id,
            defending_territory_id=defending_territory_id,
            surviving_attacking_armies=surviving_attacking_armies,
            surviving_defending_armies=surviving_defending_armies,
            fight=fight,
            fight_result=fight_result,
            player_id=player_id,
            turn=turn
            )
        )