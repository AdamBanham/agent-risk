"""
Main game event loop for the Risk simulation.
Handles pygame initialization, window management, and the core game loop.
"""

import pygame
import sys
from typing import Optional
from .renderer import GameRenderer
from .input import GameInputHandler
from .selection import TerritorySelectionHandler
from ..state.game_state import GameState, GamePhase


class GameLoop:
    """
    Main game loop for the Risk simulation. Coordinates pygame 
    initialization, event handling, and rendering.
    
    This class serves as the central coordinator for the entire Risk 
    simulation, managing the game state, rendering, input handling, and the 
    main event loop.
    """
    
    def __init__(self, width: int = 1800, height: int = 1028, 
                 regions: int = 27, num_players: int = 3, starting_armies: int = 10):
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
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.running = False
        self.renderer: Optional[GameRenderer] = None
        self.input_handler: Optional[GameInputHandler] = None
        self.selection_handler: Optional[TerritorySelectionHandler] = None
        
        # Store the current board layout for reuse
        self.current_board_layout = None
        
        # Create the game state
        self.game_state = GameState.create_new_game(regions, num_players, starting_armies)
        
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
            self.renderer = GameRenderer(self.screen, self.game_state)
            self.input_handler = GameInputHandler(self.renderer)
            self.selection_handler = TerritorySelectionHandler(self.game_state)
            
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
            self.input_handler.register_callback('regenerate_game', self._handle_regenerate_game)
            self.input_handler.register_callback('increase_regions', self._handle_increase_regions)
            self.input_handler.register_callback('increase_players', self._handle_increase_players)
            self.input_handler.register_callback('increase_armies', self._handle_increase_armies)
            
            # Register territory selection callbacks
            self.input_handler.register_callback('territory_selected', self.selection_handler.handle_territory_selected)
            self.input_handler.register_callback('territory_deselected', self.selection_handler.handle_territory_deselected)
            
            # Set up the game state - start the first turn
            if self.game_state.players:
                self.game_state.set_current_player(0)
                self.game_state.phase = GamePhase.PLAYER_TURN
            
            self.running = True
            return True
            
        except pygame.error as e:
            print(f"Failed to initialize pygame: {e}")
            return False
    
    def handle_events(self) -> None:
        """Process pygame events and user input. Delegates event processing to input handler."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            else:
                # Pass other events to input handler
                if self.input_handler:
                    self.input_handler.handle_event(event)
    
    def _handle_regenerate_game(self, input_event) -> None:
        """Handle Ctrl+R to regenerate the game state.
        
        Args:
            input_event: Input event that triggered regeneration
        """
        print("Regenerating game state with same parameters...")
        
        # Create a new game state with original parameters
        self.game_state = GameState.create_new_game(self.regions, self.num_players, self.starting_armies)
        
        # Generate the board for the new game state
        from ..state.board_generator import generate_sample_board
        generate_sample_board(self.game_state, self.width, self.height - 120)
        
        # Update renderer with new game state
        if self.renderer:
            self.renderer.game_state = self.game_state
        
        # Update selection handler with new game state
        if self.selection_handler:
            self.selection_handler.game_state = self.game_state
            self.selection_handler.clear_all_selections()
        
        # Set up the game state - start the first turn
        if self.game_state.players:
            self.game_state.set_current_player(0)
            self.game_state.phase = GamePhase.PLAYER_TURN
        
        print(f"New game state created: {self.regions} regions, {self.num_players} players, {self.starting_armies} armies each")
        print(f"Generated {len(self.game_state.territories)} territories")
        
        # Store the board layout for future reuse
        self._store_current_board_layout()
        
        # Store the board layout for future reuse
        self._store_current_board_layout()
    
    def _store_current_board_layout(self) -> None:
        """Store the current board layout for reuse when restarting with same map."""
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
        """Restore a previously stored board layout to a new game state.
        
        Args:
            game_state: GameState to restore the board layout to
        """
        if not self.current_board_layout:
            return
            
        from ..state.territory import Territory, TerritoryState
        
        # Clear existing territories
        game_state.territories.clear()
        
        # Restore territories from stored layout
        for territory_id, territory_data in self.current_board_layout['territories'].items():
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
    
    def _handle_increase_regions(self, input_event) -> None:
        """Handle Ctrl+G to increase regions and regenerate.
        
        Args:
            input_event: Input event that triggered the change
        """
        # Increase regions by 1, with a reasonable maximum
        old_regions = self.regions
        self.regions = min(self.regions + 1, 50)  # Cap at 50 regions
        
        if self.regions != old_regions:
            print(f"Increasing regions from {old_regions} to {self.regions}")
            self._regenerate_with_new_parameters()
        else:
            print(f"Already at maximum regions ({self.regions})")
    
    def _handle_increase_players(self, input_event) -> None:
        """Handle Ctrl+P to increase players and restart with same board.
        
        Args:
            input_event: Input event that triggered the change
        """
        # Increase players by 1, with a reasonable maximum
        old_players = self.num_players
        self.num_players = min(self.num_players + 1, 8)  # Cap at 8 players
        
        if self.num_players != old_players:
            print(f"Increasing players from {old_players} to {self.num_players}")
            self._restart_with_same_board()
        else:
            print(f"Already at maximum players ({self.num_players})")
    
    def _handle_increase_armies(self, input_event) -> None:
        """Handle Ctrl+S to increase starting armies and restart with same board.
        
        Args:
            input_event: Input event that triggered the change
        """
        # Increase starting armies by 1, with a reasonable maximum
        old_armies = self.starting_armies
        self.starting_armies = min(self.starting_armies + 1, 100)  # Cap at 100 armies
        
        if self.starting_armies != old_armies:
            print(f"Increasing starting armies from {old_armies} to {self.starting_armies}")
            self._restart_with_same_board()
        else:
            print(f"Already at maximum starting armies ({self.starting_armies})")
    
    def _regenerate_with_new_parameters(self) -> None:
        """Regenerate the game state with updated parameters."""
        # Create a new game state with updated parameters
        self.game_state = GameState.create_new_game(self.regions, self.num_players, self.starting_armies)
        
        # Generate the board for the new game state
        from ..state.board_generator import generate_sample_board
        generate_sample_board(self.game_state, self.width, self.height - 120)
        
        # Update renderer with new game state
        if self.renderer:
            self.renderer.game_state = self.game_state
        
        # Update selection handler with new game state
        if self.selection_handler:
            self.selection_handler.game_state = self.game_state
            self.selection_handler.clear_all_selections()
        
        # Set up the game state - start the first turn
        if self.game_state.players:
            self.game_state.set_current_player(0)
            self.game_state.phase = GamePhase.PLAYER_TURN
        
        print(f"New game created: {self.regions} regions, {self.num_players} players, {self.starting_armies} armies each")
        print(f"Generated {len(self.game_state.territories)} territories")
        
        # Store the board layout for future reuse
        self._store_current_board_layout()
    
    def _restart_with_same_board(self) -> None:
        """Restart the game with the same board layout but updated parameters."""
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
        
        # Update selection handler with new game state
        if self.selection_handler:
            self.selection_handler.game_state = self.game_state
            self.selection_handler.clear_all_selections()
        
        # Set up the game state - start the first turn
        if self.game_state.players:
            self.game_state.set_current_player(0)
            self.game_state.phase = GamePhase.PLAYER_TURN
        
        print(f"Game restarted with same board: {self.regions} regions, {self.num_players} players, {self.starting_armies} armies each")
        print(f"Reusing {len(self.game_state.territories)} territories")
    
    def _redistribute_territories_and_armies(self) -> None:
        """Redistribute territories and armies among players on the existing board."""
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
        """Update game state (placeholder for future implementation)."""
        # Update player statistics based on current territory ownership
        self.game_state.update_player_statistics()
        # TODO: Update game state, agent decisions, etc.
        pass
    
    def render(self) -> None:
        """Render the current game state."""
        if self.renderer and self.screen:
            # Clear screen with dark blue background
            self.screen.fill((20, 30, 50))
            
            # Render the board
            self.renderer.draw_board()
            
            # Update display
            pygame.display.flip()
    
    def run(self) -> None:
        """Main game loop."""
        if not self.initialize():
            return
        
        print("Starting Agent Risk simulation...")
        print("Close the window or press Ctrl+C to exit")
        
        try:
            while self.running:
                # Maintain 60 FPS
                self.clock.tick(60)
                
                # Process events
                self.handle_events()
                
                # Update game state
                self.update()
                
                # Render frame
                self.render()
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up pygame resources."""
        pygame.quit()
        print("Game loop terminated")


def main(g=2, p=2, s=10):
    """Entry point for running the game."""
    # Allow customization of game parameters
    regions = g  # Number of territories (g parameter)
    players = p  # Number of players (p parameter)
    armies = s   # Starting armies per player (s parameter)

    game = GameLoop(regions=regions, num_players=players, starting_armies=armies)
    game.run()


if __name__ == "__main__":
    main()