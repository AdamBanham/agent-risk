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
    MovementPhaseEndEvent
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
                )
            ]
            return phases 
        if isinstance(element, PlacementPhase):
            return [
                PlacementPhaseEndEvent(
                    game_state.total_turns,
                    game_state.current_player_id
                )
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
    AddArmiesSE,
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
            return super().process(game_state, element)
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

        return [
            AddArmiesSE(
                territory,
                num_troops
            )
        ]


from ..state.event_stack import (
    AttackPhase,
    AttackPhaseEndEvent,
    AttackOnTerritoryEvent,
)

class RiskAttackEngine(Engine):
    """
    The engine responsible for processing the attack phase
    of each turn in the Risk simulation.

    .. consumes ::
        - attack-phase
        - attack 
        
    .. produces ::
        - casualty-atk
        - casualty-def
        - capture 
    """
    allowed_elements = [
        AttackPhase,
        AttackOnTerritoryEvent
    ]

    def __init__(self):
        super().__init__("RiskAttackEngine")

    def processable(self, element: Union[Event, Level]) -> bool:
        return super().processable(element)

    def process(self, game_state: GameState, element: Union[Event, Level]) -> None:
        return super().process(game_state, element)

class RiskMovementEngine(Engine):
    """
    The engine responsible for processing the movement phase
    of each turn in the Risk simulation.

    .. consumes ::
        - movement-phase
        - movement

    .. produces ::

    """

    def __init__(self):
        super().__init__("RiskMovementEngine")

    def processable(self, element: Union[Event, Level]) -> bool:
        return super().processable(element)

    def process(self, game_state: GameState, element: Union[Event, Level]) -> None:
        return super().process(game_state, element)