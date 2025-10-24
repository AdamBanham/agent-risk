"""
Contains the engines for handling the turn semantics for
the Risk simulation.
"""

from .base import Engine, Event, Level
from ..state import GameState
from typing import List, Union

from ..state.event_stack import PlayingEvent, AgentTurnPhase, GameEvent

class RiskGameEngine(Engine):
    """
    The engine responsible for processing the turn-based
    mechanics of the Risk simulation.

    .. consumes ::
        - game 
        - playing

    .. produces ::
        - playing 
        - agent-turn
    """
    allowed_elements = [GameEvent, PlayingEvent]

    def __init__(self):
        super().__init__("RiskGameEngine")

    def process(self, game_state: GameState, element: Union[Event, Level]) -> None:
        ret = []
        if isinstance(element, GameEvent):
            ret.append(PlayingEvent())
            
        elif isinstance(element, PlayingEvent):
            winner = game_state.check_victory_condition()
            if winner is None:
                ret.append(PlayingEvent())
                ret.append(AgentTurnPhase(
                    game_state.total_turns,
                    game_state.current_player_id
                ))
        return ret
    
from ..state.event_stack import (
    PlacementPhase,
    AttackPhase,
    MovementPhase,
    AgentTurnEndEvent
)
from ..state.event_stack import (
    PlacementPhaseEndEvent,
    AttackPhaseEndEvent,
    MovementPhaseEndEvent,
    UpdateReinforcements,
    ClearReinforcements
)

class RiskTurnEngine(Engine):
    """
    The engine responsible for processing the agent turn phases
    of the Risk simulation.

    .. consumes ::
        - agent-turn
        - placement-end
        - attack-end
        - movement-end
        - agent-turn-end

    .. produces ::
        - shift-current-player
        - placement-phase
        - attack-phase
        - movement-phase
        - agent-turn-end
    """

    allowed_elements = [
        AgentTurnPhase,
        PlacementPhase,
        AttackPhase,
        MovementPhase,
        AgentTurnEndEvent
    ]

    def __init__(self):
        super().__init__("RiskTurnEngine")
    
    def process(self, game_state: GameState, element: Union[Event, Level]) -> None:
        if isinstance(element, AgentTurnPhase):
            phases = [
                MovementPhase(
                    game_state.total_turns,
                    game_state.current_player_id
                ),
                AttackPhase(
                    game_state.total_turns,
                    game_state.current_player_id
                ),
                PlacementPhase(
                    game_state.total_turns,
                    game_state.current_player_id
                ),
                UpdateReinforcements(
                    game_state.current_player_id
                )
            ]
            return phases 
        if isinstance(element, PlacementPhase):
            return [
                PlacementPhaseEndEvent(
                    game_state.total_turns,
                    game_state.current_player_id
                ),
            ]
        elif isinstance(element, AttackPhase):
            return [
                AttackPhaseEndEvent(
                    game_state.total_turns,
                    game_state.current_player_id
                )
            ]
        elif isinstance(element, MovementPhase):
            return [
                AgentTurnEndEvent(
                    game_state.total_turns,
                    game_state.current_player_id
                ),
                MovementPhaseEndEvent(
                    game_state.total_turns,
                    game_state.current_player_id
                )
            ]
        elif isinstance(element, AgentTurnEndEvent):
            game_state.advance_turn()
            game_state.update_player_statistics()

        return super().process(game_state, element)

from ..state.event_stack.events.turns import (
    TroopPlacementEvent
)

from ..state.event_stack import (
    AdjustArmies,
    RejectTroopPlacement
)

class RiskPlacementEngine(Engine):
    """
    The engine responsible for processing the placement phase
    of each turn in the Risk simulation.

    .. consumes ::
        - placement-phase-end
        - troop-placement

    .. produces ::
        - add-armies
        
    """
    allowed_elements = [
        PlacementPhaseEndEvent,
        TroopPlacementEvent
    ]

    def __init__(self):
        super().__init__("RiskPlacementEngine")

    def process(self, 
        game_state: GameState, element: Union[Event, Level]) -> None:

        if isinstance(element, PlacementPhaseEndEvent):
            return [
                ClearReinforcements(
                    game_state.placements_left
                )
            ]
        elif isinstance(element, TroopPlacementEvent):
            return self._handle_placement(game_state, element)
        
    def _handle_placement(self,
        game_state: GameState, element: TroopPlacementEvent
        ) -> List[Event]:
        """
        The logic to process a troop placement event.

        :param game_state: The current game state.
        :param element: The troop placement event to process.

        :returns: A list of resulting events.
        """
        territory = element.context.territory
        t_owner = game_state.get_territory(territory).owner
        num_troops = element.context.num_troops
        player = element.context.player

        if game_state.current_player_id != player:
            return [
                RejectTroopPlacement(
                    game_state.total_turns,
                    player,
                    territory,
                    num_troops,
                    "Not your turn"
                )
            ]
        if t_owner != player:
            return [
                RejectTroopPlacement(
                    game_state.total_turns,
                    player,
                    territory,
                    num_troops,
                    "You do not own this territory"
                )
            ]
        
        if game_state.placements_left < 1 \
            or num_troops > game_state.placements_left:
            return [
                RejectTroopPlacement(
                    game_state.total_turns,
                    player,
                    territory,
                    num_troops,
                    "Not enough placements left"
                )
            ]

        return [
            AdjustArmies(
                territory,
                num_troops
            )
        ]


from ..state.event_stack import (
    AttackOnTerritoryEvent,
    FightEvent,
    ResolveFightEvent,
    RejectAttack
)

from ..state import Fight, FightResult

from ..state.event_stack import (
    CaptureTerritory,
    CasualitiesOnTerritory,
    TransferArmies
)

class RiskAttackEngine(Engine):
    """
    The engine responsible for processing the attack phase
    of each turn in the Risk simulation.

    .. consumes ::
        - attack 
        - fight
        - resolve-fight
        
    .. produces ::
        - casualty-atk (SE)
        - casualty-def (SE)
        - capture (SE)
        - fight 
        - reject-attack
        - resolve-fights
    """
    allowed_elements = [
        AttackOnTerritoryEvent,
        FightEvent,
        ResolveFightEvent
    ]

    def __init__(self):
        super().__init__("RiskAttackEngine")

    def process(self, game_state: GameState, element: Union[Event, Level]) -> None:
        if isinstance(element, AttackOnTerritoryEvent):
            return self._handle_attack_request(
                game_state,
                element
            ) 
        elif isinstance(element, FightEvent):
            return self._handle_fight(
                game_state,
                element
            ) 
        elif isinstance(element, ResolveFightEvent):
            return self._handle_resolve_fight(
                game_state,
                element
            )
        return super().process(game_state, element)
    
    def _handle_attack_request(self,
        game_state: GameState,
        element: AttackOnTerritoryEvent
        ) -> List[Event]:
        
        attacker = game_state.get_territory(
            element.context.from_territory
        )
        defender = game_state.get_territory(
            element.context.to_territory
        )

        if element.context.player != game_state.current_player_id:
            return [
                RejectAttack(
                    game_state.total_turns,
                    element.context.player,
                    element.context.from_territory,
                    element.context.to_territory,
                    "Not your turn"
                )
            ]

        if element.context.player != attacker.owner:
            return [
                RejectAttack(
                    game_state.total_turns,
                    element.context.player,
                    element.context.from_territory,
                    element.context.to_territory,
                    "You do not own the attacking territory"
                )
            ]
        
        if defender not in attacker.adjacent_territories:
            return [
                RejectAttack(
                    game_state.total_turns,
                    element.context.player,
                    element.context.from_territory,
                    element.context.to_territory,
                    "Defending territory is not adjacent"
                )
            ]
        
        if defender.owner == attacker.owner:
            return [
                RejectAttack(
                    game_state.total_turns,
                    element.context.player,
                    element.context.from_territory,
                    element.context.to_territory,
                    "Cannot attack your own territory"
                )
            ]
        
        if element.context.attacking_troops >= attacker.armies \
            or element.context.attacking_troops < 1:
            return [
                RejectAttack(
                    game_state.total_turns,
                    element.context.player,
                    element.context.from_territory,
                    element.context.to_territory,
                    "Not enough troops to attack"
                )
            ]
        
        # now that rules have been validated, create FightEvent
        return [
            FightEvent(
                attacking_territory_id=attacker.id,
                defending_territory_id=defender.id,
                attacking_armies=element.context.attacking_troops,
                defending_armies=defender.armies,
                player_id=element.context.player,
                turn=game_state.total_turns
            )
        ]
        

    def _handle_fight(self,
        game_state: GameState,
        element: FightEvent
        ) -> List[Event]:
        
        # create a fight and resolve it
        fight = Fight(
            attacker_territory_id=element.context.attacking_territory_id,
            defender_territory_id=element.context.defending_territory_id,
            initial_attackers=element.context.attacking_armies,
            initial_defenders=element.context.defending_armies
        )

        result = fight.fight_to_completion()
        atk_sur, def_sur = fight.get_surviving_armies()

        return [
            ResolveFightEvent(
                attacking_territory_id=element.context.attacking_territory_id,
                defending_territory_id=element.context.defending_territory_id,
                surviving_attacking_armies=atk_sur, 
                surviving_defending_armies=def_sur,
                fight=fight, fight_result=result,
                player_id=element.context.player_id, 
                turn=element.context.turn
            )
        ]

    def _handle_resolve_fight(self,
        game_state: GameState,
        element: ResolveFightEvent
        ) -> List[Event]:
        
        fight:Fight = element.context.fight 
        atk_id = fight.attacker_territory_id
        def_id = fight.defender_territory_id
        atk_cas = fight.total_attacker_casualties
        def_cas = fight.total_defender_casualties
        atk_sur, _ = fight.get_surviving_armies()
        result:FightResult = element.context.fight_result

        ret = []

        if result.attacker_won():
            ret.append(
                TransferArmies(
                    from_territory_id=atk_id,
                    to_territory_id=def_id,
                    num_armies=atk_sur,
                )
            )
            ret.append(
                CaptureTerritory(
                    def_id,
                    element.context.player_id,
                    game_state.get_territory(def_id).owner,
                )
            )

        # report on defender losses
        if atk_cas > 0:
            ret.append(
                CasualitiesOnTerritory(
                    atk_id,
                    atk_cas
                )
            )

        # report on attacker losses
        if def_cas > 0:
            ret.append(
                CasualitiesOnTerritory(
                    def_id,
                    def_cas
                )
            )

        return ret
    
from ..state.event_stack import (
    MovementPhase,
    MovementPhaseEndEvent,
    MovementOfTroopsEvent
)
from ..state.event_stack import (
    RejectTransfer
)

class RiskMovementEngine(Engine):
    """
    The engine responsible for processing the movement phase
    of each turn in the Risk simulation.

    .. consumes ::
        - movement-phase
        - movement-of-troops

    .. produces ::
        - transfer-armies
        - reject-transfer
        - movement-phase-end
    """

    allowed_elements = [
        MovementPhaseEndEvent,
        MovementOfTroopsEvent
    ]

    def __init__(self):
        super().__init__("RiskMovementEngine")


    def process(self, game_state: GameState, element: Union[Event, Level]) -> None:
        if isinstance(element, MovementPhaseEndEvent):
            return super().process(game_state, element) 
        elif isinstance(element, MovementOfTroopsEvent):
            return self._handle_movement(
                game_state,
                element
            )
        
    def _handle_movement(self,
        game_state: GameState,
        element: MovementOfTroopsEvent
        ) -> List[Event]:
        
        from_territory = game_state.get_territory(
            element.context.from_territory
        )
        to_territory = game_state.get_territory(
            element.context.to_territory
        )
        num_troops = element.context.moving_troops
        player = element.context.player

        if game_state.current_player_id != player:
            return [
                RejectTransfer(
                    game_state.total_turns,
                    player,
                    element.context.from_territory,
                    element.context.to_territory,
                    num_troops,
                    "Not your turn"
                )
            ]
        
        if from_territory.owner != player \
            or to_territory.owner != player:
            return [
                RejectTransfer(
                    game_state.total_turns,
                    player,
                    element.context.from_territory,
                    element.context.to_territory,
                    num_troops,
                    "You do not own both territories"
                )
            ]
        
        if to_territory not in from_territory.adjacent_territories:
            return [
                RejectTransfer(
                    game_state.total_turns,
                    player,
                    element.context.from_territory,
                    element.context.to_territory,
                    num_troops,
                    "Territories are not adjacent"
                )
            ]
        
        if num_troops < 1 \
            or num_troops > from_territory.armies:
            return [
                RejectTransfer(
                    game_state.total_turns,
                    player,
                    element.context.from_territory,
                    element.context.to_territory,
                    num_troops,
                    "Not enough troops to transfer"
                )
            ]
        
        if num_troops == from_territory.armies:
            return [
                RejectTransfer(
                    game_state.total_turns,
                    player,
                    element.context.from_territory,
                    element.context.to_territory,
                    num_troops,
                    "Must leave at least one troop behind"
                )
            ]

        return [
            TransferArmies(
                from_territory_id=from_territory.id,
                to_territory_id=to_territory.id,
                num_armies=num_troops
            )
        ]
        
