"""
UI components for the Risk simulation.
Handles turn UI, phase display, buttons, and popups with clean separation from rendering.
"""

import pygame
from typing import Optional, Tuple, List, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..state import TurnState, TurnPhase, AttackState, MovementState


class UIAction(Enum):
    """UI action types that can be triggered."""
    PLACE_REINFORCEMENT = "place_reinforcement"
    UNDO_PLACEMENT = "undo_placement"
    START_ATTACK = "start_attack"
    RESOLVE_ATTACK = "resolve_attack"
    END_ATTACK = "end_attack"
    INCREASE_ATTACKING_ARMIES = "increase_attacking_armies"
    DECREASE_ATTACKING_ARMIES = "decrease_attacking_armies"
    START_MOVEMENT = "start_movement"
    EXECUTE_MOVEMENT = "execute_movement"
    END_MOVEMENT = "end_movement" 
    INCREASE_MOVING_ARMIES = "increase_moving_armies"
    DECREASE_MOVING_ARMIES = "decrease_moving_armies"
    ADVANCE_PHASE = "advance_phase"
    END_TURN = "end_turn"


@dataclass
class UIElement:
    """Base UI element with position and size."""
    x: int
    y: int
    width: int
    height: int
    visible: bool = True
    enabled: bool = True
    
    def get_rect(self) -> pygame.Rect:
        """
        Get pygame rect for this UI element.
        
        :returns: pygame.Rect representing element bounds
        """
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def contains_point(self, pos: Tuple[int, int]) -> bool:
        """
        Check if a point is inside this UI element.
        
        :param pos: Point to check (x, y)
        :returns: True if point is inside element bounds
        """
        if not self.visible or not self.enabled:
            return False
        return self.get_rect().collidepoint(pos)


@dataclass
class Button(UIElement):
    """Button UI element with text and action."""
    text: str = ""
    action: UIAction = UIAction.ADVANCE_PHASE
    font_size: int = 20
    background_color: Tuple[int, int, int] = (60, 80, 100)
    text_color: Tuple[int, int, int] = (255, 255, 255)
    hover_color: Tuple[int, int, int] = (80, 100, 120)
    disabled_color: Tuple[int, int, int] = (40, 40, 40)
    is_hovered: bool = False
    
    def get_current_background_color(self) -> Tuple[int, int, int]:
        """
        Get current background color based on state.
        
        :returns: RGB color tuple for current button state
        """
        if not self.enabled:
            return self.disabled_color
        elif self.is_hovered:
            return self.hover_color
        else:
            return self.background_color


@dataclass
class Label(UIElement):
    """Text label UI element."""
    text: str = ""
    font_size: int = 24
    text_color: Tuple[int, int, int] = (255, 255, 255)
    background_color: Optional[Tuple[int, int, int]] = None
    center_text: bool = False


@dataclass
class Counter(UIElement):
    """Counter display with +/- buttons."""
    label: str = ""
    value: int = 0
    min_value: int = 0
    max_value: int = 999
    increment_action: UIAction = UIAction.ADVANCE_PHASE
    decrement_action: UIAction = UIAction.ADVANCE_PHASE
    font_size: int = 20
    text_color: Tuple[int, int, int] = (255, 255, 255)
    button_width: int = 30


class AttackPopup:
    """Popup dialog for attack resolution."""
    
    def __init__(self, x: int, y: int, width: int = 400, height: int = 300):
        """
        Initialize attack popup.
        
        :param x: X position of popup
        :param y: Y position of popup  
        :param width: Width of popup
        :param height: Height of popup
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = False
        self.attack_state: Optional[AttackState] = None
        
        # UI elements
        self.attack_button = Button(
            x=x + 20, y=y + height - 80, width=100, height=30,
            text="Attack!", action=UIAction.RESOLVE_ATTACK
        )
        self.end_attack_button = Button(
            x=x + 140, y=y + height - 80, width=100, height=30,
            text="End Attack", action=UIAction.END_ATTACK
        )
        self.army_counter = Counter(
            x=x + 20, y=y + height - 120, width=200, height=30,
            label="Attacking Armies:", value=1, min_value=1, max_value=1,
            increment_action=UIAction.INCREASE_ATTACKING_ARMIES,
            decrement_action=UIAction.DECREASE_ATTACKING_ARMIES
        )
        
        # Colors
        self.background_color = (40, 40, 60)
        self.border_color = (100, 100, 120)
        self.text_color = (255, 255, 255)
    
    def show(self, attack_state: AttackState) -> None:
        """
        Show the attack popup with given attack state.
        
        :param attack_state: AttackState to display and manage
        """
        self.visible = True
        self.attack_state = attack_state
        
        # Update army counter limits
        self.army_counter.max_value = attack_state.max_attacking_armies
        self.army_counter.value = min(attack_state.attacking_armies, 
                                     attack_state.max_attacking_armies)
        
        # Update button states
        self.attack_button.enabled = attack_state.can_attack()
    
    def hide(self) -> None:
        """
        Hide the attack popup.
        """
        self.visible = False
        self.attack_state = None
    
    def update(self, attack_state: AttackState) -> None:
        """
        Update popup with new attack state.
        
        :param attack_state: Updated AttackState
        """
        if not self.visible:
            return
            
        self.attack_state = attack_state
        self.army_counter.max_value = attack_state.max_attacking_armies
        self.army_counter.value = attack_state.attacking_armies
        self.attack_button.enabled = attack_state.can_attack()
    
    def get_rect(self) -> pygame.Rect:
        """
        Get popup rectangle.
        
        :returns: pygame.Rect for popup bounds
        """
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def contains_point(self, pos: Tuple[int, int]) -> bool:
        """
        Check if point is inside popup.
        
        :param pos: Point to check (x, y)
        :returns: True if point is inside popup bounds
        """
        return self.visible and self.get_rect().collidepoint(pos)
    
    def get_ui_elements(self) -> List[UIElement]:
        """
        Get all interactive UI elements in the popup.
        
        :returns: List of UI elements that can be interacted with
        """
        if not self.visible:
            return []
        
        elements = [self.attack_button, self.end_attack_button]
        
        # Add counter buttons if they exist
        elements.extend([
            Button(
                x=self.army_counter.x + self.army_counter.width - 60,
                y=self.army_counter.y, width=25, height=25,
                text="+", action=self.army_counter.increment_action
            ),
            Button(
                x=self.army_counter.x + self.army_counter.width - 30,
                y=self.army_counter.y, width=25, height=25,
                text="-", action=self.army_counter.decrement_action
            )
        ])
        
        return elements


class TurnUI:
    """Main turn UI manager that coordinates all turn-related UI elements."""
    
    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize turn UI.
        
        :param screen_width: Width of game screen for positioning
        :param screen_height: Height of game screen for positioning
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # UI state
        self.current_turn: Optional[TurnState] = None
        self.ui_callbacks: Dict[UIAction, Callable] = {}
        
        # UI layout constants
        self.ui_panel_height = 120  # Height of bottom UI panel
        self.ui_y = screen_height - self.ui_panel_height
        self.margin = 10
        
        # Initialize UI elements
        self._create_ui_elements()
        
        # Popup
        popup_x = (screen_width - 400) // 2
        popup_y = (screen_height - 300) // 2
        self.attack_popup = AttackPopup(popup_x, popup_y)
        
        # Colors
        self.panel_background = (30, 40, 60)
        self.panel_border = (80, 80, 120)
        
        # Fonts
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.large_font = pygame.font.Font(None, 32)
    
    def _create_ui_elements(self) -> None:
        """
        Create and position all UI elements.
        """
        # Phase display
        self.phase_label = Label(
            x=self.margin, y=self.ui_y + self.margin,
            width=200, height=30, text="Phase: Placement",
            font_size=20
        )
        
        # Reinforcement counter (for placement phase)
        self.reinforcement_counter = Label(
            x=self.margin, y=self.ui_y + 50,
            width=200, height=30, text="Reinforcements: 0",
            font_size=18
        )
        
        # Action buttons
        button_x = 220
        button_y = self.ui_y + self.margin
        button_spacing = 110
        
        self.undo_button = Button(
            x=button_x, y=button_y, width=100, height=30,
            text="Undo (U)", action=UIAction.UNDO_PLACEMENT
        )
        
        self.advance_phase_button = Button(
            x=button_x + button_spacing, y=button_y, width=120, height=30,
            text="Next Phase", action=UIAction.ADVANCE_PHASE
        )
        
        self.end_turn_button = Button(
            x=button_x + button_spacing * 2, y=button_y, width=100, height=30,
            text="End Turn", action=UIAction.END_TURN
        )
        
        # Movement counter (for movement phase)
        self.movement_counter = Counter(
            x=button_x, y=button_y + 40, width=200, height=30,
            label="Moving Armies:", value=1, min_value=1, max_value=1,
            increment_action=UIAction.INCREASE_MOVING_ARMIES,
            decrement_action=UIAction.DECREASE_MOVING_ARMIES
        )
        
        self.execute_movement_button = Button(
            x=button_x + 220, y=button_y + 40, width=120, height=30,
            text="Move Armies", action=UIAction.EXECUTE_MOVEMENT
        )
    
    def set_turn_state(self, turn_state: Optional[TurnState]) -> None:
        """
        Update UI with new turn state.
        
        :param turn_state: Current TurnState or None if no active turn
        """
        self.current_turn = turn_state
        self._update_ui_elements()
    
    def _update_ui_elements(self) -> None:
        """
        Update UI element states based on current turn.
        """
        if not self.current_turn:
            # No active turn - hide most UI
            self.phase_label.text = "No Active Turn"
            self.reinforcement_counter.visible = False
            self.undo_button.visible = False
            self.advance_phase_button.visible = False
            self.end_turn_button.visible = False
            self.movement_counter.visible = False
            self.execute_movement_button.visible = False
            return
        
        # Update phase display
        phase_names = {
            TurnPhase.PLACEMENT: "Placement",
            TurnPhase.ATTACKING: "Attacking", 
            TurnPhase.MOVING: "Moving"
        }
        self.phase_label.text = f"Phase: {phase_names.get(self.current_turn.phase, 'Unknown')}"
        
        # Update based on current phase
        if self.current_turn.phase == TurnPhase.PLACEMENT:
            self._update_placement_ui()
        elif self.current_turn.phase == TurnPhase.ATTACKING:
            self._update_attacking_ui()
        elif self.current_turn.phase == TurnPhase.MOVING:
            self._update_moving_ui()
        
        # Update advance phase button
        self.advance_phase_button.visible = True
        if self.current_turn.phase == TurnPhase.PLACEMENT:
            self.advance_phase_button.text = "Start Attacking"
            self.advance_phase_button.enabled = (self.current_turn.reinforcements_remaining == 0)
        elif self.current_turn.phase == TurnPhase.ATTACKING:
            self.advance_phase_button.text = "Start Moving"
            self.advance_phase_button.enabled = (self.current_turn.current_attack is None)
        elif self.current_turn.phase == TurnPhase.MOVING:
            self.advance_phase_button.text = "End Turn"
            self.advance_phase_button.enabled = (self.current_turn.current_movement is None)
        
        # End turn button always visible in turn
        self.end_turn_button.visible = True
        self.end_turn_button.enabled = True
    
    def _update_placement_ui(self) -> None:
        """
        Update UI for placement phase.
        """
        self.reinforcement_counter.visible = True
        self.reinforcement_counter.text = f"Reinforcements: {self.current_turn.reinforcements_remaining}"
        
        self.undo_button.visible = True
        self.undo_button.enabled = len(self.current_turn.placements_made) > 0
        
        # Hide other phase UI
        self.movement_counter.visible = False
        self.execute_movement_button.visible = False
        self.attack_popup.hide()
    
    def _update_attacking_ui(self) -> None:
        """
        Update UI for attacking phase.
        """
        self.reinforcement_counter.visible = False
        self.undo_button.visible = False
        self.movement_counter.visible = False
        self.execute_movement_button.visible = False
        
        # Show/update attack popup if attack is active
        if self.current_turn.current_attack:
            self.attack_popup.show(self.current_turn.current_attack)
        else:
            self.attack_popup.hide()
    
    def _update_moving_ui(self) -> None:
        """
        Update UI for moving phase.
        """
        self.reinforcement_counter.visible = False
        self.undo_button.visible = False
        self.attack_popup.hide()
        
        # Show movement UI if movement is active
        if self.current_turn.current_movement:
            self.movement_counter.visible = True
            self.movement_counter.max_value = self.current_turn.current_movement.max_moving_armies
            self.movement_counter.value = self.current_turn.current_movement.moving_armies
            self.execute_movement_button.visible = True
            self.execute_movement_button.enabled = self.current_turn.current_movement.can_move()
        else:
            self.movement_counter.visible = False
            self.execute_movement_button.visible = False
    
    def register_callback(self, action: UIAction, callback: Callable) -> None:
        """
        Register callback for UI action.
        
        :param action: UIAction to listen for
        :param callback: Function to call when action is triggered
        """
        self.ui_callbacks[action] = callback
    
    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """
        Handle mouse click on UI elements.
        
        :param pos: Click position (x, y)
        :returns: True if click was handled by UI, False otherwise
        """
        if not self.current_turn:
            return False
        
        # Check attack popup first (highest priority)
        if self.attack_popup.visible and self.attack_popup.contains_point(pos):
            return self._handle_popup_click(pos)
        
        # Check main UI elements
        elements_to_check = [
            self.undo_button,
            self.advance_phase_button, 
            self.end_turn_button,
            self.execute_movement_button
        ]
        
        for element in elements_to_check:
            if element.visible and element.contains_point(pos):
                if element.enabled and element.action in self.ui_callbacks:
                    self.ui_callbacks[element.action]()
                return True
        
        # Check counter buttons for movement
        if (self.movement_counter.visible and 
            self.current_turn.phase == TurnPhase.MOVING):
            return self._handle_counter_click(pos, self.movement_counter)
        
        return False
    
    def _handle_popup_click(self, pos: Tuple[int, int]) -> bool:
        """
        Handle click on attack popup elements.
        
        :param pos: Click position (x, y)
        :returns: True if click was handled
        """
        for element in self.attack_popup.get_ui_elements():
            if element.contains_point(pos):
                if element.enabled and element.action in self.ui_callbacks:
                    self.ui_callbacks[element.action]()
                return True
        return True  # Consume click even if no element hit (prevent click-through)
    
    def _handle_counter_click(self, pos: Tuple[int, int], counter: Counter) -> bool:
        """
        Handle click on counter +/- buttons.
        
        :param pos: Click position (x, y)
        :param counter: Counter to check buttons for
        :returns: True if click was handled
        """
        # Plus button
        plus_rect = pygame.Rect(
            counter.x + counter.width - 60, counter.y, 25, 25
        )
        if plus_rect.collidepoint(pos):
            if counter.increment_action in self.ui_callbacks:
                self.ui_callbacks[counter.increment_action]()
            return True
        
        # Minus button  
        minus_rect = pygame.Rect(
            counter.x + counter.width - 30, counter.y, 25, 25
        )
        if minus_rect.collidepoint(pos):
            if counter.decrement_action in self.ui_callbacks:
                self.ui_callbacks[counter.decrement_action]()
            return True
        
        return False
    
    def handle_key_press(self, key: int) -> bool:
        """
        Handle keyboard shortcuts for UI actions.
        
        :param key: Pygame key constant
        :returns: True if key was handled by UI, False otherwise
        """
        if not self.current_turn:
            return False
        
        # U key for undo (placement phase)
        if (key == pygame.K_u and 
            self.current_turn.phase == TurnPhase.PLACEMENT and
            self.undo_button.enabled):
            if UIAction.UNDO_PLACEMENT in self.ui_callbacks:
                self.ui_callbacks[UIAction.UNDO_PLACEMENT]()
            return True
        
        # Enter/Space for advance phase
        if key in [pygame.K_RETURN, pygame.K_SPACE]:
            if self.advance_phase_button.enabled:
                if UIAction.ADVANCE_PHASE in self.ui_callbacks:
                    self.ui_callbacks[UIAction.ADVANCE_PHASE]()
                return True
        
        # Number keys for army selection (in attack/move phases)
        if pygame.K_1 <= key <= pygame.K_9:
            number = key - pygame.K_0
            
            if (self.current_turn.phase == TurnPhase.ATTACKING and 
                self.current_turn.current_attack):
                # Set attacking armies
                max_armies = self.current_turn.current_attack.max_attacking_armies
                if 1 <= number <= max_armies:
                    self.current_turn.current_attack.attacking_armies = number
                    self.attack_popup.update(self.current_turn.current_attack)
                return True
            
            elif (self.current_turn.phase == TurnPhase.MOVING and 
                  self.current_turn.current_movement):
                # Set moving armies
                max_armies = self.current_turn.current_movement.max_moving_armies
                if 1 <= number <= max_armies:
                    self.current_turn.current_movement.moving_armies = number
                    self._update_moving_ui()
                return True
        
        return False
    
    def update_hover_states(self, mouse_pos: Tuple[int, int]) -> None:
        """
        Update hover states for UI elements.
        
        :param mouse_pos: Current mouse position (x, y)
        """
        if not self.current_turn:
            return
        
        # Update button hover states
        buttons = [
            self.undo_button,
            self.advance_phase_button,
            self.end_turn_button,
            self.execute_movement_button
        ]
        
        for button in buttons:
            if button.visible:
                button.is_hovered = button.contains_point(mouse_pos)
        
        # Update popup button hover states
        if self.attack_popup.visible:
            for element in self.attack_popup.get_ui_elements():
                if hasattr(element, 'is_hovered'):
                    element.is_hovered = element.contains_point(mouse_pos)
    
    def get_ui_rect(self) -> pygame.Rect:
        """
        Get the rectangle covering the entire UI panel.
        
        :returns: pygame.Rect for UI panel bounds
        """
        return pygame.Rect(0, self.ui_y, self.screen_width, self.ui_panel_height)