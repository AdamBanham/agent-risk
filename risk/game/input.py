"""
Input handling for the Risk simulation.
Processes pygame events, mouse clicks, and keyboard input.
"""

import pygame
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass


@dataclass
class InputEvent:
    """Represents a processed input event."""
    event_type: str
    position: Optional[tuple] = None
    key: Optional[int] = None
    button: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


class InputHandler:
    """Handles user input events for the Risk game."""
    
    def __init__(self):
        """Initialize the input handler."""
        self.callbacks: Dict[str, Callable] = {}
        self.mouse_position = (0, 0)
        self.mouse_pressed = False
        self.keys_pressed = set()
        
        # Event type mappings
        self.event_mappings = {
            pygame.MOUSEBUTTONDOWN: 'mouse_down',
            pygame.MOUSEBUTTONUP: 'mouse_up',
            pygame.MOUSEMOTION: 'mouse_move',
            pygame.KEYDOWN: 'key_down',
            pygame.KEYUP: 'key_up',
        }
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback function for a specific event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        self.callbacks[event_type] = callback
    
    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a pygame event and trigger appropriate callbacks.
        
        Args:
            event: Pygame event to process
        """
        # Update input state
        self._update_input_state(event)
        
        # Map pygame event to our event system
        if event.type in self.event_mappings:
            event_type = self.event_mappings[event.type]
            input_event = self._create_input_event(event, event_type)
            
            # Trigger callback if registered
            if event_type in self.callbacks:
                self.callbacks[event_type](input_event)
        
        # Handle special events
        self._handle_special_events(event)
    
    def _update_input_state(self, event: pygame.event.Event) -> None:
        """Update internal input state tracking.
        
        Args:
            event: Pygame event
        """
        if event.type == pygame.MOUSEMOTION:
            self.mouse_position = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse_pressed = False
        elif event.type == pygame.KEYDOWN:
            self.keys_pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self.keys_pressed.discard(event.key)
    
    def _create_input_event(self, pygame_event: pygame.event.Event, 
                          event_type: str) -> InputEvent:
        """Create an InputEvent from a pygame event.
        
        Args:
            pygame_event: Original pygame event
            event_type: Mapped event type string
            
        Returns:
            InputEvent object
        """
        input_event = InputEvent(event_type=event_type)
        
        # Add position for mouse events
        if hasattr(pygame_event, 'pos'):
            input_event.position = pygame_event.pos
        
        # Add key for keyboard events
        if hasattr(pygame_event, 'key'):
            input_event.key = pygame_event.key
        
        # Add button for mouse events
        if hasattr(pygame_event, 'button'):
            input_event.button = pygame_event.button
        
        # Add any additional data
        input_event.data = {
            'mouse_position': self.mouse_position,
            'mouse_pressed': self.mouse_pressed,
            'keys_pressed': list(self.keys_pressed),
        }
        
        return input_event
    
    def _handle_special_events(self, event: pygame.event.Event) -> None:
        """Handle special keyboard shortcuts and events.
        
        Args:
            event: Pygame event
        """
        if event.type == pygame.KEYDOWN:
            # ESC key to quit
            if event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            
            # Ctrl+R to regenerate game state
            elif event.key == pygame.K_r and (pygame.K_LCTRL in self.keys_pressed or pygame.K_RCTRL in self.keys_pressed):
                if 'regenerate_game' in self.callbacks:
                    input_event = InputEvent(
                        event_type='regenerate_game',
                        key=event.key,
                        data={'ctrl_pressed': True}
                    )
                    self.callbacks['regenerate_game'](input_event)
                    print("Regenerating game state...")
            
            # Ctrl+G to increase regions
            elif event.key == pygame.K_g and (pygame.K_LCTRL in self.keys_pressed or pygame.K_RCTRL in self.keys_pressed):
                if 'increase_regions' in self.callbacks:
                    input_event = InputEvent(
                        event_type='increase_regions',
                        key=event.key,
                        data={'ctrl_pressed': True}
                    )
                    self.callbacks['increase_regions'](input_event)
                    print("Increasing regions...")
            
            # Ctrl+P to increase players
            elif event.key == pygame.K_p and (pygame.K_LCTRL in self.keys_pressed or pygame.K_RCTRL in self.keys_pressed):
                if 'increase_players' in self.callbacks:
                    input_event = InputEvent(
                        event_type='increase_players',
                        key=event.key,
                        data={'ctrl_pressed': True}
                    )
                    self.callbacks['increase_players'](input_event)
                    print("Increasing players (keeping same map)...")
            
            # Ctrl+S to increase starting army size
            elif event.key == pygame.K_s and (pygame.K_LCTRL in self.keys_pressed or pygame.K_RCTRL in self.keys_pressed):
                if 'increase_armies' in self.callbacks:
                    input_event = InputEvent(
                        event_type='increase_armies',
                        key=event.key,
                        data={'ctrl_pressed': True}
                    )
                    self.callbacks['increase_armies'](input_event)
                    print("Increasing starting armies (keeping same map)...")
            
            # Space key for pause/unpause (placeholder)
            elif event.key == pygame.K_SPACE:
                if 'toggle_pause' in self.callbacks:
                    self.callbacks['toggle_pause'](None)
            
            # Number keys for quick actions (placeholder)
            elif pygame.K_1 <= event.key <= pygame.K_9:
                number = event.key - pygame.K_0
                if 'number_key' in self.callbacks:
                    input_event = InputEvent(
                        event_type='number_key',
                        key=event.key,
                        data={'number': number}
                    )
                    self.callbacks['number_key'](input_event)
    
    def is_key_pressed(self, key: int) -> bool:
        """Check if a specific key is currently pressed.
        
        Args:
            key: Pygame key constant
            
        Returns:
            True if key is pressed, False otherwise
        """
        return key in self.keys_pressed
    
    def get_mouse_position(self) -> tuple:
        """Get current mouse position.
        
        Returns:
            Tuple of (x, y) mouse coordinates
        """
        return self.mouse_position
    
    def is_mouse_pressed(self) -> bool:
        """Check if mouse is currently pressed.
        
        Returns:
            True if mouse is pressed, False otherwise
        """
        return self.mouse_pressed


class GameInputHandler(InputHandler):
    """Extended input handler with game-specific functionality."""
    
    def __init__(self, renderer=None):
        """Initialize game input handler.
        
        Args:
            renderer: Game renderer for territory selection
        """
        super().__init__()
        self.renderer = renderer
        self.selected_territory = None
        
        # Register default game callbacks
        self.register_callback('mouse_down', self._handle_mouse_click)
        self.register_callback('key_down', self._handle_key_press)
    
    def _handle_mouse_click(self, input_event: InputEvent) -> None:
        """Handle mouse click events for territory selection.
        
        Args:
            input_event: Input event with click information
        """
        if not self.renderer or not input_event.position:
            return
        
        # Check if click is on a territory
        territory = self.renderer.get_territory_at_position(input_event.position)
        if territory:
            self.selected_territory = territory
            
            # Emit territory selection event
            territory_event = InputEvent(
                event_type='territory_selected',
                position=input_event.position,
                data={
                    'territory_id': territory.id,
                    'territory': territory,
                    'mouse_position': input_event.position
                }
            )
            
            # Trigger territory selection callback if registered
            if 'territory_selected' in self.callbacks:
                self.callbacks['territory_selected'](territory_event)
            
            print(f"Selected territory: {territory.name} (ID: {territory.id})")
            print(f"  Owner: Player {territory.owner + 1 if territory.owner is not None else 'None'}")
            print(f"  Armies: {territory.armies}")
            print(f"  Continent: {territory.continent}")
        else:
            self.selected_territory = None
            
            # Emit territory deselection event
            deselect_event = InputEvent(
                event_type='territory_deselected',
                position=input_event.position,
                data={
                    'mouse_position': input_event.position
                }
            )
            
            # Trigger territory deselection callback if registered
            if 'territory_deselected' in self.callbacks:
                self.callbacks['territory_deselected'](deselect_event)
            
            print("Clicked on empty area")
    
    def _handle_key_press(self, input_event: InputEvent) -> None:
        """Handle keyboard input for game actions.
        
        Args:
            input_event: Input event with key information
        """
        if not input_event.key:
            return
        
        # Print current selection info
        if input_event.key == pygame.K_i and self.selected_territory:
            print(f"\\nTerritory Info: {self.selected_territory.name}")
            print(f"  ID: {self.selected_territory.id}")
            print(f"  Position: {self.selected_territory.center}")
            print(f"  Owner: {self.selected_territory.owner}")
            print(f"  Armies: {self.selected_territory.armies}")
            print(f"  Continent: {self.selected_territory.continent}")
        
        # Toggle debug info
        elif input_event.key == pygame.K_d:
            print("\\n=== Debug Info ===")
            print(f"Mouse position: {self.get_mouse_position()}")
            print(f"Selected territory: {self.selected_territory.name if self.selected_territory else 'None'}")
            print(f"Keys pressed: {[pygame.key.name(k) for k in self.keys_pressed]}")
        
        # Print help
        elif input_event.key == pygame.K_h:
            self._print_help()
    
    def _print_help(self) -> None:
        """Print help information to console."""
        print("\\n=== Agent Risk Controls ===")
        print("Mouse:")
        print("  - Click on territories to select them (yellow outline, red text)")
        print("  - Click empty area to deselect all")
        print("Keyboard:")
        print("  - ESC: Quit game")
        print("  - Ctrl+R: Regenerate game state/board")
        print("  - Ctrl+G: Increase regions (+1)")
        print("  - Ctrl+P: Increase players (+1, keeps same map)")
        print("  - Ctrl+S: Increase starting armies (+1, keeps same map)")
        print("  - Space: Pause/unpause (placeholder)")
        print("  - I: Show info for selected territory")
        print("  - D: Show debug information")
        print("  - H: Show this help")
        print("  - 1-9: Quick actions (placeholder)")
        print("========================\\n")