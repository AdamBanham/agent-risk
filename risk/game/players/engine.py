from typing import List, Union, Optional

from risk.state.event_stack.events.turns import AttackPhaseEndEvent

from ...engine import Engine
from ...state.game_state import GameState
from ...state.event_stack import Event, Level
from ...state.turn_manager import TurnManager, TurnPhase

from ...state.event_stack import (
    PlacementPhase,
    AttackPhase,
    MovementPhase,
    SystemInterruptEvent,
    SystemStepEvent,
    TerritorySelectedEvent,
    ChangeSelectedTerritoryEvent
)

class PlayerEngine(Engine):
    """
    Base engine for handling player actions in the game.
    """

    allowed_elements = [
        PlacementPhase,
        AttackPhase,
        MovementPhase,
        TerritorySelectedEvent
    ]

    def process(self, 
        state: GameState, element: Union[Event, Level]
        ) -> Optional[List[Event]]:
        
        if isinstance(element, TerritorySelectedEvent):

            return [
                ChangeSelectedTerritoryEvent(
                    territory_id=element.context.territory_id,
                    previous_territory_id=state.ui_state.selected_territory_id
                
                ),
                SystemStepEvent()
            ]

        player = state.get_player(state.current_player_id)

        if player and player.is_human:
            # Defer to human player input handling
            return [
                SystemInterruptEvent()
            ]
        
        return super().process(state, element)
    
from ...state.event_stack import (
    TroopPlacementEvent,
    PlacementPhaseEndEvent
)
        
class PlayerPlacementEngine(Engine):
    """
    Engine specifically for handling player placement phases.
    """

    allowed_elements = [
        PlacementPhase,
        ChangeSelectedTerritoryEvent,
        PlacementPhaseEndEvent,
        Event
    ]

    def __init__(self):
        super().__init__("Player Placement Engine")

    def process(self, 
        state: GameState, element: Union[Event, Level]
        ) -> Optional[List[Event]]:

        manager = state.ui_turn_manager

        if manager and manager.current_turn and manager.current_turn.phase == TurnPhase.PLACEMENT:
            manager.current_turn.reinforcements_remaining = state.placements_left

        player = state.get_player(state.current_player_id)
        if player and not player.is_human:
            return super().process(state, element)
        
        
        if isinstance(element, PlacementPhase):
            # trigger the start of the player's turn
            manager.start_player_turn(state.current_player_id)
            return super().process(state, element)
    
        if isinstance(element, ChangeSelectedTerritoryEvent):

            if manager.current_turn.phase == TurnPhase.PLACEMENT:
                return [
                    TroopPlacementEvent(
                        turn=state.total_turns,
                        player=state.current_player_id,
                        territory=element.context.new_territory_id,
                        num_troops=1  # Placeholder for actual player input
                    ),
                ]
        
        if isinstance(element, PlacementPhaseEndEvent):
            print("moving to next phase")
            manager.advance_turn_phase()

        return super().process(state, element)
    
from ...state.event_stack import (
    TriggerAttackPopupEvent,
)

class PlayerAttackEngine(Engine):
    """
    Engine specifically for handling player attack phases.
    """

    allowed_elements = [
        AttackPhase,
        ChangeSelectedTerritoryEvent,
        AttackPhaseEndEvent
    ]

    def __init__(self,):
        super().__init__("Player Attack Engine")

    def process(self, 
        state: GameState, element: Union[Event, Level]
        ) -> Optional[List[Event]]:

        manager = state.ui_turn_manager
        player = state.get_player(state.current_player_id)

        if player and not player.is_human:
            return super().process(state, element)

        if manager and manager.current_turn and manager.current_turn.phase != TurnPhase.ATTACKING:
            return super().process(state, element)
        
        if isinstance(element, AttackPhase):
            # trigger the start of the player's turn
            return super().process(state, element)
    
        if isinstance(element, ChangeSelectedTerritoryEvent):
            # Placeholder for actual attack handling logic

            attacker = element.context.previous_territory_id
            defender = element.context.new_territory_id


            actioned = manager.current_turn.start_attack(
                attacker_territory=state.get_territory(attacker),
                defender_territory=state.get_territory(defender)
            )

            if actioned:
                state.ui_turn_state.attack_popup.show(
                    manager.current_turn.current_attack
                )

            return super().process(state, element)
        
        if isinstance(element, AttackPhaseEndEvent):
            print("moving to next phase")
            manager.advance_turn_phase()

        return super().process(state, element)
    
from ...state.event_stack import (
    UIActionEvent,
    FightEvent,
    SystemResumeEvent,
)
from ...state.ui import UIAction

class UITriggersEngine(Engine):
    """
    Engine to handle UI-triggered events.
    """

    allowed_elements = [
        UIActionEvent
    ]

    def __init__(self):
        super().__init__("UI Triggers Engine")

    def process(self, 
        state: GameState, element: Union[Event, Level]
        ) -> Optional[List[Event]]:

        manager = state.ui_turn_manager
        cur_turn = manager.current_turn if manager else None
        cur_atk = cur_turn.current_attack if cur_turn else None


        match element.context.action:

            case UIAction.INCREASE_ATTACKING_ARMIES if cur_atk:
                cur_atk.attacking_armies = min(
                    cur_atk.attacking_armies + 1,
                    cur_atk.max_attacking_armies
                )
            case UIAction.DECREASE_ATTACKING_ARMIES if cur_atk:
                cur_atk.attacking_armies = max(
                    0, 
                    cur_atk.attacking_armies - 1
                )
            case UIAction.END_ATTACK:
                if cur_turn:
                    cur_turn.end_attack()
                state.ui_turn_state.attack_popup.hide()
            case UIAction.RESOLVE_ATTACK if cur_atk and cur_turn:
                ret = [
                    FightEvent(
                        cur_atk.attacker_territory_id,
                        cur_atk.defender_territory_id,
                        cur_atk.attacking_armies,
                        cur_atk.defending_armies,
                        state.current_player_id,
                        state.total_turns
                    ),
                ]
                cur_turn.end_attack()
                state.ui_turn_state.attack_popup.hide()
                return ret
            case UIAction.END_TURN:
                if manager:
                    manager.end_current_turn()
                return [
                    SystemResumeEvent(),
                    SystemStepEvent()
                ]
            case UIAction.ADVANCE_PHASE:
                if manager:
                    manager.advance_turn_phase()
                return [
                    SystemResumeEvent(),
                    SystemStepEvent()
                ]
        
        return super().process(state, element)