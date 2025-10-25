"""
Input handling for the Risk simulation.
Processes pygame events, mouse clicks, and keyboard input.
"""

import pygame
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

from ..state.ui import TurnUI


@dataclass
class InputEvent:
    """Represents a processed input event."""

    event_type: str
    position: Optional[tuple] = None
    key: Optional[int] = None
    button: Optional[int] = None
    data: Optional[Dict[str, Any]] = None


class InputHandler:
    """Handles user input events for the Risk game. Processes pygame events and triggers registered callbacks.

    This class provides a layer of abstraction between pygame events and game logic,
    allowing components to register for specific event types and receive processed input events.
    """

    def __init__(self):
        """
        Initialize the input handler. Sets up event mappings and state
        tracking.
        """
        self.callbacks: Dict[str, Callable] = {}
        self.mouse_position = (0, 0)
        self.mouse_pressed = False
        self.keys_pressed = set()

        # Event type mappings
        self.event_mappings = {
            pygame.MOUSEBUTTONDOWN: "mouse_down",
            pygame.MOUSEBUTTONUP: "mouse_up",
            pygame.MOUSEMOTION: "mouse_move",
            pygame.KEYDOWN: "key_down",
            pygame.KEYUP: "key_up",
        }

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback function for a specific event type. Allows
        components to respond to input events.

        :param event_type: Type of event to listen for (e.g., 'mouse_down',
                          'key_down')
        :param callback: Function to call when event occurs
        """
        self.callbacks[event_type] = callback

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Process a pygame event and trigger appropriate callbacks. Maps pygame
        events to internal event system.

        :param event: Pygame event to process and potentially trigger
                     callbacks for
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
        """
        Update internal input state tracking. Maintains current mouse
        position and key press state.

        :param event: Pygame event to update state from
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

    def _create_input_event(
        self, pygame_event: pygame.event.Event, event_type: str
    ) -> InputEvent:
        """Create an InputEvent from a pygame event. Converts pygame events to internal event representation.

        :param pygame_event: Original pygame event to convert
        :param event_type: Mapped event type string for internal system
        :returns: InputEvent object with extracted event data
        """
        input_event = InputEvent(event_type=event_type)

        # Add position for mouse events
        if hasattr(pygame_event, "pos"):
            input_event.position = pygame_event.pos

        # Add key for keyboard events
        if hasattr(pygame_event, "key"):
            input_event.key = pygame_event.key

        # Add button for mouse events
        if hasattr(pygame_event, "button"):
            input_event.button = pygame_event.button

        # Add any additional data
        input_event.data = {
            "mouse_position": self.mouse_position,
            "mouse_pressed": self.mouse_pressed,
            "keys_pressed": list(self.keys_pressed),
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

            # Ctrl+R to trigger sim resume
            elif event.key == pygame.K_r and (
                pygame.K_LCTRL in self.keys_pressed
                or pygame.K_RCTRL in self.keys_pressed
            ):
                if "sim_resume" in self.callbacks:
                    input_event = InputEvent(
                        event_type="sim_resume",
                        key=event.key,
                        data={"ctrl_pressed": True},
                    )
                    self.callbacks["sim_resume"](input_event)

            # Ctrl+S to increase starting army size
            elif event.key == pygame.K_s and (
                pygame.K_LCTRL in self.keys_pressed
                or pygame.K_RCTRL in self.keys_pressed
            ):
                if "sim_step" in self.callbacks:
                    input_event = InputEvent(
                        event_type="sim_step",
                        key=event.key,
                        data={"ctrl_pressed": True},
                    )
                    self.callbacks["sim_step"](input_event)

            # ctrl+I to trigger sim interrupt
            elif event.key == pygame.K_i and (
                pygame.K_LCTRL in self.keys_pressed
                or pygame.K_RCTRL in self.keys_pressed
            ):
                if "sim_interrupt" in self.callbacks:
                    input_event = InputEvent(
                        event_type="sim_interrupt",
                        key=event.key,
                        data={"ctrl_pressed": True},
                    )
                    self.callbacks["sim_interrupt"](input_event)

            # ctrl+'+' to increase sim speed
            elif event.key == pygame.K_EQUALS and (
                pygame.K_LCTRL in self.keys_pressed
                or pygame.K_RCTRL in self.keys_pressed
            ):
                if "increase_sim_speed" in self.callbacks:
                    input_event = InputEvent(
                        event_type="increase_sim_speed",
                        key=event.key,
                        data={"ctrl_pressed": True},
                    )
                    self.callbacks["increase_sim_speed"](input_event)

            # ctrl+'-' to decrease sim speed
            elif event.key == pygame.K_MINUS and (
                pygame.K_LCTRL in self.keys_pressed
                or pygame.K_RCTRL in self.keys_pressed
            ):
                if "decrease_sim_speed" in self.callbacks:
                    input_event = InputEvent(
                        event_type="decrease_sim_speed",
                        key=event.key,
                        data={"ctrl_pressed": True},
                    )
                    self.callbacks["decrease_sim_speed"](input_event)

            # Space key for pause/unpause - but check turn UI first
            elif event.key == pygame.K_SPACE:
                # If there's a turn UI, let it handle space first (for phase advancement)
                # Otherwise, use space for global pause/unpause
                if "toggle_pause" in self.callbacks:
                    input_event = InputEvent(
                        event_type="toggle_pause",
                        key=event.key,
                        data={"space_pressed": True},
                    )
                    self.callbacks["toggle_pause"](input_event)

            # Number keys for quick actions (placeholder)
            elif pygame.K_1 <= event.key <= pygame.K_9:
                number = event.key - pygame.K_0
                if "number_key" in self.callbacks:
                    input_event = InputEvent(
                        event_type="number_key", key=event.key, data={"number": number}
                    )
                    self.callbacks["number_key"](input_event)

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

    def __init__(self, renderer=None, turn_ui: Optional[TurnUI] = None):
        """Initialize game input handler.

        Args:
            renderer: Game renderer for territory selection
            turn_ui: Turn UI manager for turn-based interactions
        """
        super().__init__()
        self.renderer = renderer
        self.turn_ui = turn_ui
        self.selected_territory = None

        # Register default game callbacks
        self.register_callback("mouse_down", self._handle_mouse_click)
        self.register_callback("key_down", self._handle_key_press)

    def _handle_mouse_click(self, input_event: InputEvent) -> None:
        """Handle mouse click events for territory selection.

        Args:
            input_event: Input event with click information
        """

        if not input_event.position:
            return

        # Check turn UI first (higher priority than territory selection)
        if self.turn_ui and self.turn_ui.handle_click(input_event.position):
            return  # UI handled the click

        if not self.renderer:
            return

        # Check if click is on a territory
        territory = self.renderer.get_territory_at_position(input_event.position)
        if territory:
            self.selected_territory = territory

            # Emit territory selection event
            territory_event = InputEvent(
                event_type="territory_selected",
                position=input_event.position,
                data={
                    "territory_id": territory.id,
                    "territory": territory,
                    "mouse_position": input_event.position,
                },
            )

            # Trigger territory selection callback if registered
            if "territory_selected" in self.callbacks:
                self.callbacks["territory_selected"](territory_event)

            print(f"Selected territory: {territory.name} (ID: {territory.id})")
            print(
                f"  Owner: Player {territory.owner + 1 if territory.owner is not None else 'None'}"
            )
            print(f"  Armies: {territory.armies}")
            print(f"  Continent: {territory.continent}")
        else:
            self.selected_territory = None

            # Emit territory deselection event
            deselect_event = InputEvent(
                event_type="territory_deselected",
                position=input_event.position,
                data={"mouse_position": input_event.position},
            )

            # Trigger territory deselection callback if registered
            if "territory_deselected" in self.callbacks:
                self.callbacks["territory_deselected"](deselect_event)

            print("Clicked on empty area")

    def _handle_key_press(self, input_event: InputEvent) -> None:
        """Handle keyboard input for game actions.

        Args:
            input_event: Input event with key information
        """
        if not input_event.key:
            return

        # Special case for space key: turn UI takes priority over global pause
        if input_event.key == pygame.K_SPACE:
            # If turn UI can handle space (for phase advancement), let it do so
            if self.turn_ui and self.turn_ui.handle_key_press(input_event.key):
                return  # UI handled the space key for phase advancement
            # Otherwise, let global pause handling occur (in parent _handle_special_events)
            return

        # Check turn UI first for other turn-specific shortcuts
        if self.turn_ui and self.turn_ui.handle_key_press(input_event.key):
            return  # UI handled the key

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
            print(
                f"Selected territory: {self.selected_territory.name if self.selected_territory else 'None'}"
            )
            print(f"Keys pressed: {[pygame.key.name(k) for k in self.keys_pressed]}")

        # Print help
        elif input_event.key == pygame.K_h:
            self._print_help()

    def _print_help(self) -> None:
        """
        Print help information to console.
        """
        print("\\n=== Agent Risk Controls ===")
        print("Mouse:")
        print("  - Click on territories to select them (yellow outline, red text)")
        print("  - Click empty area to deselect all")
        print("  - Click on UI buttons to perform actions")
        print("Keyboard:")
        print("  - ESC: Quit game")
        print("  - Ctrl+R: Regenerate game state/board")
        print("  - Ctrl+G: Increase regions (+1)")
        print("  - Ctrl+P: Increase players (+1, keeps same map)")
        print("  - Ctrl+S: Increase starting armies (+1, keeps same map)")
        print("  - Space: Pause/unpause simulation (or advance phase in turns)")
        print("  - I: Show info for selected territory")
        print("  - D: Show debug information")
        print("  - H: Show this help")
        print("  - 1-9: Quick actions (placeholder)")
        print("Turn Controls:")
        print("  - U: Undo last placement (in placement phase)")
        print("  - Enter/Space: Advance to next phase")
        print("  - 1-9: Set army count (in attack/move phases)")
        print(
            "Note: Space advances phase when turn UI is active, otherwise pauses simulation"
        )
        print("========================\\n")

    def update_mouse_hover(self, mouse_pos: Tuple[int, int]) -> None:
        """
        Update UI hover states based on mouse position.

        :param mouse_pos: Current mouse position (x, y)
        """
        if self.turn_ui:
            self.turn_ui.update_hover_states(mouse_pos)

    def set_turn_ui(self, turn_ui: TurnUI) -> None:
        """
        Set the turn UI manager for this input handler.

        :param turn_ui: TurnUI instance to handle
        """
        self.turn_ui = turn_ui
