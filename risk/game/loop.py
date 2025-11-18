"""
Main game event loop for the Risk simulation.
Handles pygame initialization, window management, and the core game loop.
"""

import asyncio
import time
import pygame
from typing import Optional

from risk.engine.risk import RiskSimulationController
from risk.utils.logging import info
from risk.game.rendering.stack_renderer import StackRenderer
from risk.state.event_stack.events.players import TerritorySelectedEvent
from risk.state.event_stack.events.ui import UIActionEvent
from .renderer import GameRenderer
from .rendering.animations import AnimationEngine
from .rendering.player_movements import PlayerMovementRenderer
from .players import add_player_engines

from .input import GameInputHandler, InputEvent
from .selection import TerritorySelectionHandler
from ..state.game_state import GameState
from ..state.turn_manager import TurnManager
from ..state.ui import UIAction, TurnUI


class GameLoop:
    """
    Main game loop for the Risk simulation. Coordinates pygame
    initialization, event handling, and rendering.

    This class serves as the central coordinator for the entire Risk
    simulation, managing the game state, rendering, input handling, and the
    main event loop.
    """

    def __init__(
        self,
        width: int = 1800,
        height: int = 1028,
        regions: int = 27,
        num_players: int = 3,
        starting_armies: int = 10,
        play_from_state: Optional[GameState] = None,
        sim_delay: float = 1.0,
        sim_speed: int = 5,
    ) -> None:
        """
        Initialize pygame and create the game window. Sets up game
        parameters and creates initial game state.

        :param width: Window width in pixels
        :param height: Window height in pixels
        :param regions: Number of territories to generate (g parameter)
        :param num_players: Number of players in the simulation (p parameter)
        :param starting_armies: Starting army size per player (s parameter)
        """
        self.width = width
        self.height = height
        self.regions = regions
        self.num_players = num_players
        self.starting_armies = starting_armies
        self.sim_delay = sim_delay
        self._sim_speed = sim_speed
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.running = False
        self.paused = False
        self.renderer: Optional[GameRenderer] = None
        self.input_handler: Optional[GameInputHandler] = None
        self.selection_handler: Optional[TerritorySelectionHandler] = None
        self.turn_manager: Optional[TurnManager] = None

        # Store the current board layout for reuse
        self.current_board_layout = None

        # Create the game state
        if play_from_state:
            self.game_state = play_from_state
            self.regions = len(play_from_state.territories)
            self.num_players = len(play_from_state.players)
        else:
            self.game_state = GameState.create_new_game(
                regions, num_players, starting_armies
            )
            self.game_state.initialise()

        # create event stack for simulation
        self.sim_controller = RiskSimulationController(self.game_state)
        add_player_engines(self.sim_controller, self.turn_manager)

        self.stack = self.sim_controller.event_stack

    def initialize(self) -> bool:
        """
        Initialize pygame and create game components. Sets up screen,
        components, and registers callbacks.

        :returns: True if initialization successful, False otherwise
        """
        try:
            pygame.init()
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Agent Risk - Dynamic Board Simulation")
            self.clock = pygame.time.Clock()

            # Initialize game components
            turn_manager = self.game_state.ui_turn_manager
            ui = self.game_state.ui_turn_state

            if not turn_manager:
                self.game_state.ui_turn_manager = TurnManager(self.game_state)
                turn_manager = self.game_state.ui_turn_manager
            
            if not ui:
                self.game_state.ui_turn_state = TurnUI(
                    self.game_state.screen_width,
                    self.game_state.screen_height
                )
                ui = self.game_state.ui_turn_state

            self.renderer = GameRenderer(self.screen, self.game_state)
            self.renderer.add_renderer(StackRenderer(self.stack))
            self.renderer.add_renderer(PlayerMovementRenderer())
            self.sim_controller.add_engine(
                AnimationEngine(self.renderer.animation_manager)
            )
            self.input_handler = GameInputHandler(self.renderer, ui)
            self.selection_handler = TerritorySelectionHandler(
                self.game_state, turn_manager
            )

            # Set up selection callbacks for turn actions
            self.selection_handler.set_action_callbacks(
                placement_callback=lambda: None,
                attack_callback=lambda: None,  # Attack is handled by UI popup
                movement_callback=lambda: None,  # Movement is handled by UI
            )

            # Register callbacks for game state regeneration and parameter changes
            self.input_handler.register_callback(
                "toggle_pause", self._handle_toggle_pause
            )
            self.input_handler.register_callback("sim_step", self._push_sim_sys_step)
            self.input_handler.register_callback(
                "sim_interrupt", self._push_sim_sys_interrupt
            )
            self.input_handler.register_callback(
                "sim_resume", self._push_sim_sys_resume
            )
            self.input_handler.register_callback(
                "increase_sim_speed", self._increase_sim_speed
            )
            self.input_handler.register_callback(
                "decrease_sim_speed", self._decrease_sim_speed
            )

            # Register territory selection callbacks
            self.input_handler.register_callback(
                "territory_selected", self._handle_selection
            )
            self.input_handler.register_callback(
                "territory_deselected",
                self.selection_handler.handle_territory_deselected,
            )

            def launch_ui_action(action: UIAction):
                self.sim_controller.force_processing_of(UIActionEvent(action, dict()))

            # register other input callbacks as needed
            for value in list(UIAction):

                def make_callback(that=value):
                    return lambda: launch_ui_action(that)

                ui.register_callback(value, make_callback(value))

            # Connect turn UI to input handler
            self.input_handler.set_turn_ui(ui)
            self.running = True
            return True

        except pygame.error as e:
            print(f"Failed to initialize pygame: {e}")
            return False

    def _handle_selection(self, input_event: InputEvent) -> None:
        """
        Handle territory selection events.

        :param input_event: Input event containing selection details
        """
        territory_id = input_event.data["territory_id"]

        self.sim_controller.force_processing_of(TerritorySelectedEvent(territory_id))

        if territory_id is not None and self.selection_handler:
            self.selection_handler.handle_territory_selected(input_event)

    def handle_events(self) -> None:
        """
        Process pygame events and user input. Delegates event processing to
        input handler and updates UI hover states.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            else:
                # Pass other events to input handler
                if self.input_handler:
                    self.input_handler.handle_event(event)

        # Update UI hover states
        if self.input_handler:
            mouse_pos = pygame.mouse.get_pos()
            self.input_handler.update_mouse_hover(mouse_pos)

    def _increase_sim_speed(self, input_event) -> None:
        """
        Increase the simulation speed by reducing the delay between steps.

        :param input_event: Input event that triggered the speed increase
        """
        # Decrease delay to speed up simulation, with a minimum cap
        self._sim_speed = self._sim_speed * 2

    def _decrease_sim_speed(self, input_event) -> None:
        """
        Decrease the simulation speed by increasing the delay between steps.

        :param input_event: Input event that triggered the speed decrease
        """
        # Increase delay to slow down simulation, with a maximum cap
        self._sim_speed = max(1, self._sim_speed // 2)

    def _handle_toggle_pause(self, input_event) -> None:
        """
        Handle spacebar to toggle pause/unpause state.

        :param input_event: Input event that triggered the pause toggle
        """
        from ..state.event_stack import (
            SystemInterruptEvent,
            SystemStepEvent,
            SystemResumeEvent,
        )

        self.paused = not self.paused
        status = "PAUSED" if self.paused else "UNPAUSED"

        if self.paused:
            self.sim_controller.force_processing_of(SystemInterruptEvent())
        else:
            self.sim_controller.force_processing_of(SystemResumeEvent())

        # Update window title to show pause state
        if self.paused:
            pygame.display.set_caption("Agent Risk - Dynamic Board Simulation [PAUSED]")
        else:
            pygame.display.set_caption("Agent Risk - Dynamic Board Simulation")

    def _push_sim_sys_step(self, input_event) -> None:
        """
        Push a SystemStepEvent to the simulation event stack.

        :param input_event: Input event that triggered the step
        """
        from ..state.event_stack import SystemStepEvent

        self.sim_controller.event_stack.push(SystemStepEvent())
        pygame.display.set_caption("Agent Risk - Dynamic Board Simulation [STEPPED]")

    def _push_sim_sys_interrupt(self, input_event) -> None:
        """
        Push a SystemInterruptEvent to the simulation event stack.

        :param input_event: Input event that triggered the interrupt
        """
        from ..state.event_stack import SystemInterruptEvent

        self.sim_controller.event_stack.push(SystemInterruptEvent())
        pygame.display.set_caption("Agent Risk - Dynamic Board Simulation [INTERUPTED]")

    def _push_sim_sys_resume(self, input_event) -> None:
        """
        Push a SystemResumeEvent to the simulation event stack.

        :param input_event: Input event that triggered the resume
        """
        from ..state.event_stack import SystemResumeEvent

        self.sim_controller.force_processing_of(SystemResumeEvent())
        pygame.display.set_caption("Agent Risk - Dynamic Board Simulation")

    def update(self) -> None:
        """
        Update game state (only when not paused).
        """
        if not self.paused:
            # Update player statistics based on current territory ownership
            self.game_state.update_player_statistics()
            self.game_state.ui_turn_state.set_turn_state(
                self.game_state.ui_turn_manager.current_turn
            )
            self.input_handler.set_turn_ui(self.game_state.ui_turn_state)

    def render(self, delta_time: float) -> None:
        """
        Render the current game state.

        :param delta_time: Time elapsed since last frame in seconds
        """
        if self.renderer and self.screen:
            # Clear screen with dark blue background
            self.screen.fill((20, 30, 50))

            # Render the board with delta time for animations
            self.renderer.draw_board(delta_time)

            # If paused, show pause overlay
            if self.paused:
                self._draw_pause_overlay()

            # Update display
            pygame.display.flip()

    def _draw_pause_overlay(self) -> None:
        """
        Draw pause overlay on the screen.
        """
        if not self.screen:
            return

        # Create semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(128)  # Semi-transparent
        overlay.fill((0, 0, 0))  # Black overlay
        self.screen.blit(overlay, (0, 0))

        # Initialize font if not already done
        pygame.font.init()

        # Draw pause text
        font_large = pygame.font.Font(None, 72)
        font_small = pygame.font.Font(None, 36)

        # Main pause text
        pause_text = font_large.render("PAUSED", True, (255, 255, 255))
        pause_rect = pause_text.get_rect(
            center=(self.width // 2, self.height // 2 - 30)
        )
        self.screen.blit(pause_text, pause_rect)

        # Instruction text
        instruction_text = font_small.render(
            "Press SPACE to resume", True, (200, 200, 200)
        )
        instruction_rect = instruction_text.get_rect(
            center=(self.width // 2, self.height // 2 + 30)
        )
        self.screen.blit(instruction_text, instruction_rect)

    async def run_async(self) -> None:
        """Async main loop with concurrent simulation and rendering."""

        # Create concurrent tasks
        sim_task = asyncio.create_task(self._simulation_loop())
        render_task = asyncio.create_task(self._render_loop())

        try:
            await asyncio.gather(sim_task, render_task)
        finally:
            self.cleanup()

    async def _simulation_loop(self) -> None:
        """Async simulation loop."""
        processed = 0
        while self.running:
            if not self.paused:
                step_time = time.time()
                # batch processing to speed up simulation
                for _ in range(self._sim_speed):
                    action = self.sim_controller.step()
                    if action:
                        processed += 1

                if processed > 0:
                    elapsed = time.time() - step_time
                    self._caption = f"Agent Risk - Dynamic Board Simulation ({processed:0d} actions/render) (processed in {elapsed:.4f} seconds)"
                    info("Simulation step took {:.4f} seconds for {processed:0d} actions".format(elapsed, processed=processed))
                processed = 0

            # release control back to draw
            await asyncio.sleep(self.sim_delay)

    async def _render_loop(self) -> None:
        """Async rendering loop."""
        while self.running:
            delta_time = self.clock.tick(60) / 1000.0
            self.update()
            self.handle_events()
            self.render(delta_time)
            pygame.display.set_caption(
                getattr(self, "_caption", "Agent Risk - Dynamic Board Simulation")
            )
            await asyncio.sleep(0)  # Yield control

    def run(self) -> None:
        """
        Main game loop.
        """
        if not self.initialize():
            return

        print("Starting Agent Risk simulation...")
        print("Close the window or press Ctrl+C to exit")

        try:
            asyncio.run(self.run_async())

        except KeyboardInterrupt:
            print("\nShutting down...")

        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """
        Clean up pygame resources.
        """
        pygame.quit()
        print("Game loop terminated")


def main(g=2, p=2, s=10):
    """
    Entry point for running the game.

    :param g: Number of regions/territories to generate
    :param p: Number of players in the simulation
    :param s: Starting army size per player
    """
    # Allow customization of game parameters
    regions = g  # Number of territories (g parameter)
    players = p  # Number of players (p parameter)
    armies = s  # Starting armies per player (s parameter)

    game = GameLoop(regions=regions, num_players=players, starting_armies=armies)
    game.run()


if __name__ == "__main__":
    main()
