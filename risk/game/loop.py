"""
Main game event loop for the Risk simulation.
Handles pygame initialization, window management, and the core game loop.
"""

import time
import pygame
from typing import Optional

from risk.engine.risk import RiskSimulationController
from risk.game.rendering.stack_renderer import StackRenderer
from .renderer import GameRenderer
from .rendering.animations import AnimationEngine

from .input import GameInputHandler
from .selection import TerritorySelectionHandler
from .ui import UIAction
from ..state.game_state import GameState, GamePhase
from ..state.turn_manager import TurnManager, TurnPhase


class GameLoop:
    """
    Main game loop for the Risk simulation. Coordinates pygame 
    initialization, event handling, and rendering.
    
    This class serves as the central coordinator for the entire Risk 
    simulation, managing the game state, rendering, input handling, and the 
    main event loop.
    """
    
    def __init__(self, width: int = 1800, height: int = 1028, 
                 regions: int = 27, num_players: int = 3, 
                 starting_armies: int = 10,
                 play_from_state: Optional[GameState] = None,
                 sim_delay: float = 1.0) -> None:
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
            self.game_state = GameState.create_new_game(regions, num_players, starting_armies)
        
        # create event stack for simulation
        self.sim_controller = RiskSimulationController(self.game_state)
        self.stack = self.sim_controller.event_stack
        
    def initialize(self) -> bool:
        """Initialize pygame and create game components. Sets up screen, components, and registers callbacks.
        
        :returns: True if initialization successful, False otherwise
        """
        try:
            pygame.init()
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Agent Risk - Dynamic Board Simulation")
            self.clock = pygame.time.Clock()
            
            # Initialize game components
            self.turn_manager = TurnManager(self.game_state)
            # Register animation callbacks with turn manager
            self.turn_manager.set_attack_animation_callback(
                self._handle_attack_animation
            )
            self.turn_manager.set_attack_success_callback(
                self._handle_attack_success_animation
            )
            self.turn_manager.set_attack_failure_callback(
                self._handle_attack_failure_animation
            )
            self.renderer = GameRenderer(self.screen, self.game_state)
            self.renderer.add_renderer(
                StackRenderer(self.stack)
            )
            self.sim_controller.add_engine(
                AnimationEngine(self.renderer.animation_manager)
            )
            self.input_handler = GameInputHandler(self.renderer, self.renderer.get_turn_ui())
            self.selection_handler = TerritorySelectionHandler(self.game_state, self.turn_manager)
            
            # Connect turn UI to input handler
            self.input_handler.set_turn_ui(self.renderer.get_turn_ui())
            
            # Set up selection callbacks for turn actions
            self.selection_handler.set_action_callbacks(
                placement_callback=self._handle_place_reinforcement,
                attack_callback=lambda: None,  # Attack is handled by UI popup
                movement_callback=lambda: None  # Movement is handled by UI
            )
            
            # Store the board layout after renderer potentially generates it
            if self.game_state.territories:
                self._store_current_board_layout()
            
            # Generate initial board if not already present (fallback)
            if not self.game_state.territories:
                from ..state.board_generator import generate_sample_board
                generate_sample_board(self.game_state, self.width, self.height - 120)
                print(f"Generated initial board with {len(self.game_state.territories)} territories")
                
                # Store the initial board layout
                self._store_current_board_layout()
            
            # Register callbacks for game state regeneration and parameter changes
            self.input_handler.register_callback('toggle_pause', self._handle_toggle_pause)
            self.input_handler.register_callback('sim_step', self._push_sim_sys_step)
            self.input_handler.register_callback('sim_interrupt', self._push_sim_sys_interrupt)
            self.input_handler.register_callback('sim_resume', self._push_sim_sys_resume)
            
            # Register territory selection callbacks
            self.input_handler.register_callback('territory_selected', self.selection_handler.handle_territory_selected)
            self.input_handler.register_callback('territory_deselected', self.selection_handler.handle_territory_deselected)
            
            # Register turn UI callbacks
            self._register_turn_ui_callbacks()
            
            # Set up the game state - start the first turn
            if self.game_state.players and self.turn_manager:
                self.game_state.set_current_player(0)
                self.game_state.phase = GamePhase.PLAYER_TURN
                
                # Start first player's turn
                self.turn_manager.start_player_turn(0)
                current_turn = self.turn_manager.get_current_turn()
                if current_turn and self.renderer:
                    self.renderer.set_turn_state(current_turn)
            
            self.running = True
            return True
            
        except pygame.error as e:
            print(f"Failed to initialize pygame: {e}")
            return False
    
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
    
    def _handle_regenerate_game(self, input_event) -> None:
        """
        Handle Ctrl+R to regenerate the game state.
        
        :param input_event: Input event that triggered regeneration
        """
        print("Regenerating game state with same parameters...")
        
        # Create a new game state with original parameters
        self.game_state = GameState.create_new_game(self.regions, 
                                                    self.num_players, 
                                                    self.starting_armies)
        
        # Generate the board for the new game state
        from ..state.board_generator import generate_sample_board
        generate_sample_board(self.game_state, self.width, self.height - 120)
        
        # Update all components with new game state
        if self.turn_manager:
            self.turn_manager.game_state = self.game_state
        
        if self.renderer:
            self.renderer.game_state = self.game_state
        
        if self.selection_handler:
            self.selection_handler.game_state = self.game_state
            self.selection_handler.clear_all_selections()
        
        # Set up the game state - start the first turn
        if self.game_state.players and self.turn_manager:
            self.game_state.set_current_player(0)
            self.game_state.phase = GamePhase.PLAYER_TURN
            
            # Start first player's turn
            self.turn_manager.start_player_turn(0)
            current_turn = self.turn_manager.get_current_turn()
            if current_turn and self.renderer:
                self.renderer.set_turn_state(current_turn)
        
        print(f"New game state created: {self.regions} regions, "
              f"{self.num_players} players, {self.starting_armies} armies each")
        print(f"Generated {len(self.game_state.territories)} territories")
        
        # Store the board layout for future reuse
        self._store_current_board_layout()
    
    def _store_current_board_layout(self) -> None:
        """
        Store the current board layout for reuse when restarting with same 
        map.
        """
        if not self.game_state.territories:
            return
            
        # Store essential board layout information
        self.current_board_layout = {
            'territories': {},
            'adjacencies': {}
        }
        
        # Store territory geometry and metadata
        for territory_id, territory in self.game_state.territories.items():
            self.current_board_layout['territories'][territory_id] = {
                'name': territory.name,
                'center': territory.center,
                'vertices': territory.vertices.copy(),
                'continent': territory.continent,
                'adjacent_territories': territory.adjacent_territories.copy()
            }
    
    def _restore_board_layout(self, game_state: GameState) -> None:
        """
        Restore a previously stored board layout to a new game state.
        
        :param game_state: GameState to restore the board layout to
        """
        if not self.current_board_layout:
            return
            
        from ..state.territory import Territory, TerritoryState
        
        # Clear existing territories
        game_state.territories.clear()
        
        # Restore territories from stored layout
        for territory_id, territory_data in (
            self.current_board_layout['territories'].items()):
            territory = Territory(
                id=territory_id,
                name=territory_data['name'],
                center=territory_data['center'],
                vertices=territory_data['vertices'],
                continent=territory_data['continent'],
                state=TerritoryState.FREE,
                owner=None,
                armies=0,
                adjacent_territories=territory_data['adjacent_territories'].copy()
            )
            game_state.add_territory(territory)
    
    def _handle_toggle_pause(self, input_event) -> None:
        """
        Handle spacebar to toggle pause/unpause state.
        
        :param input_event: Input event that triggered the pause toggle
        """
        from ..state.event_stack import (
            SystemInterruptEvent,
            SystemStepEvent,
            SystemResumeEvent
        )

        self.paused = not self.paused
        status = "PAUSED" if self.paused else "UNPAUSED"
        print(f"Game {status}")

        if self.paused:
            self.sim_controller.event_stack.push(
                SystemInterruptEvent()
            )
        else:
            self.sim_controller.event_stack.push(
                SystemResumeEvent()
            )
            self.sim_controller.event_stack.push(
                SystemStepEvent()
            )
        
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
        self.sim_controller.event_stack.push(
            SystemStepEvent()
        )
        pygame.display.set_caption("Agent Risk - Dynamic Board Simulation [STEPPED]")

    def _push_sim_sys_interrupt(self, input_event) -> None:
        """
        Push a SystemInterruptEvent to the simulation event stack.
        
        :param input_event: Input event that triggered the interrupt
        """
        from ..state.event_stack import SystemInterruptEvent
        self.sim_controller.event_stack.push(
            SystemInterruptEvent()
        )
        pygame.display.set_caption("Agent Risk - Dynamic Board Simulation [INTERUPTED]")

    def _push_sim_sys_resume(self, input_event) -> None:
        """
        Push a SystemResumeEvent to the simulation event stack.
        
        :param input_event: Input event that triggered the resume
        """
        from ..state.event_stack import SystemResumeEvent
        self.sim_controller.force_processing_of(
            SystemResumeEvent()
        )
        pygame.display.set_caption("Agent Risk - Dynamic Board Simulation")
    
    def _regenerate_with_new_parameters(self) -> None:
        """
        Regenerate the game state with updated parameters.
        """
        # Create a new game state with updated parameters
        self.game_state = GameState.create_new_game(self.regions, self.num_players, self.starting_armies)
        
        # Generate the board for the new game state
        from ..state.board_generator import generate_sample_board
        generate_sample_board(self.game_state, self.width, self.height - 120)
        
        # Update renderer with new game state
        if self.renderer:
            self.renderer.game_state = self.game_state
            # Clear any ongoing animations when regenerating
            self.renderer.clear_animations()
        
        # Update selection handler with new game state
        if self.selection_handler:
            self.selection_handler.game_state = self.game_state
            self.selection_handler.clear_all_selections()
        
        # Recreate turn manager with new game state and register animation callbacks
        if self.game_state.players:
            self.turn_manager = TurnManager(self.game_state)
            self.turn_manager.set_attack_animation_callback(
                self._handle_attack_animation
            )
            self.turn_manager.set_attack_success_callback(
                self._handle_attack_success_animation
            )
            self.turn_manager.set_attack_failure_callback(
                self._handle_attack_failure_animation
            )
        
        # Set up the game state - start the first turn
        if self.game_state.players:
            self.game_state.set_current_player(0)
            self.game_state.phase = GamePhase.PLAYER_TURN
        
        print(f"New game created: {self.regions} regions, {self.num_players} players, {self.starting_armies} armies each")
        print(f"Generated {len(self.game_state.territories)} territories")
    
    def _handle_attack_animation(self, attacker_territory_id: int, 
                                 defender_territory_id: int, player_id: int) -> None:
        """
        Handle attack animation trigger from turn manager. Creates arrow 
        animation from attacking to defending territory with player color.
        
        :param attacker_territory_id: ID of attacking territory
        :param defender_territory_id: ID of defending territory
        :param player_id: ID of attacking player for color matching
        """
        if self.renderer:
            self.renderer.start_attack_arrow_animation(
                attacker_territory_id, 
                defender_territory_id,
                player_id
            )
    
    def _handle_attack_success_animation(self, territory_id: int, 
                                       player_id: int) -> None:
        """
        Handle attack success animation trigger from turn manager. Creates 
        tick animation at conquered territory after arrow completes.
        
        :param territory_id: ID of conquered territory
        :param player_id: ID of attacking player
        """
        if self.renderer:
            self.renderer.start_attack_success_animation(territory_id, player_id, arrow_duration=1.2)
    
    def _handle_attack_failure_animation(self, territory_id: int, 
                                       player_id: int) -> None:
        """
        Handle attack failure animation trigger from turn manager. Creates 
        cross animation at defended territory after arrow completes.
        
        :param territory_id: ID of defended territory
        :param player_id: ID of attacking player
        """
        if self.renderer:
            self.renderer.start_attack_failure_animation(territory_id, player_id, arrow_duration=1.2)
        
        # Store the board layout for future reuse
        self._store_current_board_layout()
    
    def _restart_with_same_board(self) -> None:
        """
        Restart the game with the same board layout but updated parameters.
        """
        if not self.current_board_layout:
            print("No board layout stored, regenerating new board...")
            self._regenerate_with_new_parameters()
            return
        
        # Create a new game state with updated parameters
        self.game_state = GameState.create_new_game(self.regions, self.num_players, self.starting_armies)
        
        # Restore the stored board layout
        self._restore_board_layout(self.game_state)
        
        # Redistribute territories and armies among players
        self._redistribute_territories_and_armies()
        
        # Update renderer with new game state
        if self.renderer:
            self.renderer.game_state = self.game_state
            # Clear any ongoing animations when restarting
            self.renderer.clear_animations()
        
        # Update selection handler with new game state
        if self.selection_handler:
            self.selection_handler.game_state = self.game_state
            self.selection_handler.clear_all_selections()
        
        # Recreate turn manager with new game state and register animation callbacks
        if self.game_state.players:
            self.turn_manager = TurnManager(self.game_state)
            self.turn_manager.set_attack_animation_callback(
                self._handle_attack_animation
            )
            self.turn_manager.set_attack_success_callback(
                self._handle_attack_success_animation
            )
            self.turn_manager.set_attack_failure_callback(
                self._handle_attack_failure_animation
            )
        
        # Set up the game state - start the first turn
        if self.game_state.players:
            self.game_state.set_current_player(0)
            self.game_state.phase = GamePhase.PLAYER_TURN
        
        print(f"Game restarted with same board: {self.regions} regions, {self.num_players} players, {self.starting_armies} armies each")
        print(f"Reusing {len(self.game_state.territories)} territories")
    
    def _redistribute_territories_and_armies(self) -> None:
        """
        Redistribute territories and armies among players on the existing 
        board.
        """
        if not self.game_state.territories or not self.game_state.players:
            return
        
        import random
        
        # Get list of all territories
        territories = list(self.game_state.territories.values())
        players = list(self.game_state.players.values())
        
        if not territories or not players:
            return
        
        # Reset all territories to free state
        for territory in territories:
            territory.set_owner(None, 0)
        
        # Randomly assign territories to players
        random.shuffle(territories)
        for i, territory in enumerate(territories):
            player_id = players[i % len(players)].id
            territory.set_owner(player_id, 1)  # Start with 1 army per territory
        
        # Distribute remaining armies to each player individually to reach exactly s armies per player
        for player in players:
            # Get territories owned by this player
            player_territories = [t for t in territories if t.owner == player.id]
            
            # Calculate current army count for this player
            current_armies = sum(t.armies for t in player_territories)
            
            # Calculate remaining armies needed to reach starting_armies per player
            remaining_armies_needed = self.starting_armies - current_armies
            
            # Distribute remaining armies randomly among this player's territories
            for _ in range(remaining_armies_needed):
                if player_territories:  # Safety check
                    territory = random.choice(player_territories)
                    territory.armies += 1
        
        # Verify army distribution is correct
        for player in players:
            player_territories = [t for t in territories if t.owner == player.id]
            total_armies = sum(t.armies for t in player_territories)
            print(f"Player {player.id} ({player.name}): {len(player_territories)} territories, {total_armies} armies (expected: {self.starting_armies})")
            
            if total_armies != self.starting_armies:
                print(f"WARNING: Player {player.id} has {total_armies} armies but should have {self.starting_armies}")
    
    def update(self) -> None:
        """
        Update game state (only when not paused).
        """
        if not self.paused:
            # Update player statistics based on current territory ownership
            self.game_state.update_player_statistics()
            # TODO: Update game state, agent decisions, etc.
    
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
        pause_rect = pause_text.get_rect(center=(self.width // 2, self.height // 2 - 30))
        self.screen.blit(pause_text, pause_rect)
        
        # Instruction text
        instruction_text = font_small.render("Press SPACE to resume", True, (200, 200, 200))
        instruction_rect = instruction_text.get_rect(center=(self.width // 2, self.height // 2 + 30))
        self.screen.blit(instruction_text, instruction_rect)
    
    def run(self) -> None:
        """
        Main game loop.
        """
        if not self.initialize():
            return
        
        print("Starting Agent Risk simulation...")
        print("Close the window or press Ctrl+C to exit")
        
        try:
            last_tick = 0
            processed = 0
            started = time.time()
            
            while self.running:
                # Maintain 60 FPS and get delta time
                delta_time = self.clock.tick(120) / 1000.0  # Convert milliseconds to seconds
                last_tick += delta_time
                # step simulator
                if last_tick > self.sim_delay:
                    last_tick = 0
                    action = self.sim_controller.step()
                    if action:
                        processed += 1

                    if time.time() - started > 5:
                        fps = processed / (time.time() - started)
                        pygame.display.set_caption(f"Agent Risk - Dynamic Board Simulation ({fps:.2f} steps/sec)")
                        started = time.time()
                        processed = 0

                # Process events
                self.handle_events()
                
                # Update game state
                self.update()
                
                # Render frame with delta time
                self.render(delta_time)
                
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
    
    def _register_turn_ui_callbacks(self) -> None:
        """
        Register callbacks for turn UI actions.
        """
        if not self.renderer or not self.turn_manager:
            return
        
        turn_ui = self.renderer.get_turn_ui()
        
        # Register all turn UI action callbacks
        turn_ui.register_callback(UIAction.PLACE_REINFORCEMENT, self._handle_place_reinforcement)
        turn_ui.register_callback(UIAction.UNDO_PLACEMENT, self._handle_undo_placement)
        turn_ui.register_callback(UIAction.START_ATTACK, self._handle_start_attack)
        turn_ui.register_callback(UIAction.RESOLVE_ATTACK, self._handle_resolve_attack)
        turn_ui.register_callback(UIAction.END_ATTACK, self._handle_end_attack)
        turn_ui.register_callback(UIAction.INCREASE_ATTACKING_ARMIES, self._handle_increase_attacking_armies)
        turn_ui.register_callback(UIAction.DECREASE_ATTACKING_ARMIES, self._handle_decrease_attacking_armies)
        turn_ui.register_callback(UIAction.START_MOVEMENT, self._handle_start_movement)
        turn_ui.register_callback(UIAction.EXECUTE_MOVEMENT, self._handle_execute_movement)
        turn_ui.register_callback(UIAction.END_MOVEMENT, self._handle_end_movement)
        turn_ui.register_callback(UIAction.INCREASE_MOVING_ARMIES, self._handle_increase_moving_armies)
        turn_ui.register_callback(UIAction.DECREASE_MOVING_ARMIES, self._handle_decrease_moving_armies)
        turn_ui.register_callback(UIAction.ADVANCE_PHASE, self._handle_advance_phase)
        turn_ui.register_callback(UIAction.END_TURN, self._handle_end_turn)
    
    # Turn Action Handlers
    def _handle_place_reinforcement(self) -> None:
        """Handle reinforcement placement on selected territory."""
        if not self.turn_manager or not self.selection_handler:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or current_turn.phase != TurnPhase.PLACEMENT:
            return
        
        selected_territory = self.selection_handler.get_primary_selected_territory()
        if not selected_territory:
            print("No territory selected for reinforcement placement")
            return
        
        # Check if player owns the territory
        if selected_territory.owner != current_turn.player_id:
            print("Cannot place reinforcements on territory you don't own")
            return
        
        # Place reinforcement
        if current_turn.place_reinforcement(selected_territory.id, 1):
            selected_territory.armies += 1
            print(f"Placed 1 reinforcement on {selected_territory.name}")
            
            # Update renderer with new turn state
            if self.renderer:
                self.renderer.set_turn_state(current_turn)
        else:
            print("Cannot place reinforcement - no reinforcements available")
    
    def _handle_undo_placement(self) -> None:
        """Handle undoing the last reinforcement placement."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or current_turn.phase != TurnPhase.PLACEMENT:
            return
        
        undo_result = current_turn.undo_last_placement()
        if undo_result:
            territory_id, armies = undo_result
            territory = self.game_state.get_territory(territory_id)
            if territory:
                territory.armies -= armies
                print(f"Undid placement of {armies} armies from {territory.name}")
                
                # Update renderer with new turn state
                if self.renderer:
                    self.renderer.set_turn_state(current_turn)
        else:
            print("No placements to undo")
    
    def _handle_start_attack(self) -> None:
        """Handle starting an attack between selected territories.""" 
        if not self.turn_manager or not self.selection_handler:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or current_turn.phase != TurnPhase.ATTACKING:
            return
        
        # Need exactly one selected territory to attack from
        selected_territories = self.selection_handler.get_selected_territories()
        if len(selected_territories) != 1:
            print("Select exactly one territory to attack from")
            return
        
        attacker_territory = self.selection_handler.get_primary_selected_territory()
        if not attacker_territory:
            return
        
        # For now, user needs to click on adjacent territory to attack
        # This would be enhanced with better UI flow
        print(f"Attack mode: {attacker_territory.name} ready to attack. Click on adjacent enemy territory.")
    
    def _handle_resolve_attack(self) -> None:
        """Handle resolving the current attack using the Fight system."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or not current_turn.current_attack:
            return
        
        # Resolve attack using Fight system
        result = current_turn.resolve_attack()
        fight = current_turn.current_fight
        if result:

            attacker = fight.attacker_territory_id
            defender = fight.defender_territory_id

            atk_ter = self.game_state.get_territory(attacker)
            def_ter = self.game_state.get_territory(defender)

            atk_sur, def_sur = fight.get_surviving_armies()

            atk_ter.remove_armies(fight.total_attacker_casualties)
            def_ter.remove_armies(fight.total_defender_casualties)

            print("DEBUG: \n",fight.get_battle_summary())

            if result.attacker_won():
                def_ter.set_owner(current_turn.player_id, atk_sur)
                print(f"Attack succeeded: {atk_ter.name} conquered {def_ter.name}")
            elif result.defender_won():
                print(f"Attack failed: {def_ter.name} defended against {atk_ter.name}")
                if def_sur == 0:
                    print(f"WARNING: Defender has 0 surviving armies after winning the fight")
                    def_ter.set_owner(None, 0)  # Territory becomes free

            # Update game state
            self.game_state.update_player_statistics()
            
            # Update renderer
            if self.renderer:
                self.renderer.set_turn_state(current_turn)
    
    def _handle_end_attack(self) -> None:
        """Handle ending the current attack."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if current_turn:
            current_turn.end_attack()
            print("Attack ended")
            
            # Update renderer
            if self.renderer:
                self.renderer.set_turn_state(current_turn)
    
    def _handle_increase_attacking_armies(self) -> None:
        """Handle increasing attacking army count."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if current_turn and current_turn.current_attack:
            attack = current_turn.current_attack
            if attack.attacking_armies < attack.max_attacking_armies:
                attack.attacking_armies += 1
                
                # Update renderer
                if self.renderer:
                    self.renderer.set_turn_state(current_turn)
    
    def _handle_decrease_attacking_armies(self) -> None:
        """Handle decreasing attacking army count."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if current_turn and current_turn.current_attack:
            attack = current_turn.current_attack
            if attack.attacking_armies > 1:
                attack.attacking_armies -= 1
                
                # Update renderer
                if self.renderer:
                    self.renderer.set_turn_state(current_turn)
    
    def _handle_start_movement(self) -> None:
        """Handle starting troop movement between selected territories."""
        if not self.turn_manager or not self.selection_handler:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or current_turn.phase != TurnPhase.MOVING:
            return
        
        # Need exactly one selected territory to move from
        selected_territories = self.selection_handler.get_selected_territories()
        if len(selected_territories) != 1:
            print("Select exactly one territory to move armies from")
            return
        
        source_territory = self.selection_handler.get_primary_selected_territory()
        if not source_territory:
            return
        
        print(f"Movement mode: {source_territory.name} ready to move armies. Click on adjacent owned territory.")
    
    def _handle_execute_movement(self) -> None:
        """Handle executing the current movement."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or not current_turn.current_movement:
            return
        
        # Execute movement
        result = current_turn.execute_movement()
        if result:
            # Apply movement to territories
            source_territory = self.game_state.get_territory(result['source_territory_id'])
            target_territory = self.game_state.get_territory(result['target_territory_id'])
            
            if source_territory and target_territory:
                source_territory.armies -= result['armies_moved']
                target_territory.armies += result['armies_moved']
                
                print(f"Moved {result['armies_moved']} armies from {source_territory.name} to {target_territory.name}")
                
                # Add random walk animation for movement
                if self.renderer:
                    self.renderer.start_movement_animation(
                        source_territory_id=result['source_territory_id'],
                        target_territory_id=result['target_territory_id'],
                        duration=1.5
                    )
                
                # Update renderer
                if self.renderer:
                    self.renderer.set_turn_state(current_turn)
    
    def _handle_end_movement(self) -> None:
        """Handle ending the current movement."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if current_turn:
            current_turn.end_movement()
            print("Movement ended")
            
            # Update renderer
            if self.renderer:
                self.renderer.set_turn_state(current_turn)
    
    def _handle_increase_moving_armies(self) -> None:
        """Handle increasing moving army count."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if current_turn and current_turn.current_movement:
            movement = current_turn.current_movement
            if movement.moving_armies < movement.max_moving_armies:
                movement.moving_armies += 1
                
                # Update renderer
                if self.renderer:
                    self.renderer.set_turn_state(current_turn)
    
    def _handle_decrease_moving_armies(self) -> None:
        """Handle decreasing moving army count."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if current_turn and current_turn.current_movement:
            movement = current_turn.current_movement
            if movement.moving_armies > 1:
                movement.moving_armies -= 1
                
                # Update renderer
                if self.renderer:
                    self.renderer.set_turn_state(current_turn)
    
    def _handle_advance_phase(self) -> None:
        """Handle advancing to the next turn phase."""
        if not self.turn_manager:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn:
            return
        
        # Check if phase can be advanced
        if not self.turn_manager.can_advance_phase():
            print("Cannot advance phase yet")
            return
        
        # Advance phase
        phase_continued = self.turn_manager.advance_turn_phase()
        if phase_continued:
            print(f"Advanced to {current_turn.phase.value} phase")
        else:
            # Turn ended, advance to next player
            self._handle_end_turn()
            return
        
        # Update renderer
        if self.renderer:
            self.renderer.set_turn_state(current_turn)
    
    def _handle_end_turn(self) -> None:
        """Handle ending the current player's turn."""
        if not self.turn_manager:
            return
        
        current_player_id = self.game_state.current_player_id
        current_player = self.game_state.get_player(current_player_id) if current_player_id is not None else None
        
        # End current turn and start next player's turn
        if self.turn_manager.end_current_turn():
            next_player_id = self.game_state.current_player_id
            next_player = self.game_state.get_player(next_player_id) if next_player_id is not None else None
            
            print(f"Turn ended for {current_player.name if current_player else 'Unknown'}")
            print(f"Starting turn for {next_player.name if next_player else 'Unknown'}")
            
            # Update renderer with new turn state
            if self.renderer:
                new_turn = self.turn_manager.get_current_turn()
                self.renderer.set_turn_state(new_turn)
        else:
            print("Game Over!")
            # TODO: Handle game end
        
        # Clear selections
        if self.selection_handler:
            self.selection_handler.clear_all_selections()


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
    armies = s   # Starting armies per player (s parameter)

    game = GameLoop(regions=regions, num_players=players, starting_armies=armies)
    game.run()


if __name__ == "__main__":
    main()