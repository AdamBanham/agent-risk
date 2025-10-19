"""
Pygame renderer for the Risk board simulation.
Handles drawing territories, armies, and game state visualization.
"""

import pygame
import math
from typing import List, Tuple, Optional, Dict

from ..state import Territory, TerritoryState, GameState, Player, TurnState
from ..state.board_generator import generate_sample_board
from .ui import TurnUI
from .ui_renderer import UIRenderer
from .animation import AnimationManager


class GameRenderer:
    """Renders the Risk board and game state using pygame."""
    
    def __init__(self, screen: pygame.Surface, game_state: GameState, 
                 turn_state: Optional[TurnState] = None):
        """Initialize the renderer. Sets up pygame rendering context and generates board if needed.
        
        :param screen: Pygame surface to draw on
        :param game_state: GameState to render
        :param turn_state: Optional TurnState for turn-based UI
        """
        self.screen = screen
        self.game_state = game_state
        self.width = screen.get_width()
        self.height = screen.get_height()
        
        # Initialize turn UI
        self.turn_ui = TurnUI(self.width, self.height)
        self.ui_renderer = UIRenderer(screen)
        self.turn_state = turn_state
        
        # Initialize animation system
        self.animation_manager = AnimationManager()
        
        # Colors
        self.colors = {
            'background': (20, 30, 50),
            'territory_border': (100, 100, 100),
            'territory_fill': (60, 80, 100),
            'continent_colors': [
                (150, 80, 80),   # Red-ish
                (80, 150, 80),   # Green-ish
                (80, 80, 150),   # Blue-ish
                (150, 150, 80),  # Yellow-ish
                (150, 80, 150),  # Purple-ish
                (80, 150, 150),  # Cyan-ish
            ],
            'player_colors': [
                (200, 50, 50),   # Red
                (50, 200, 50),   # Green
                (50, 50, 200),   # Blue
                (200, 200, 50),  # Yellow
                (200, 50, 200),  # Magenta
                (50, 200, 200),  # Cyan
                (150, 75, 0),    # Brown
                (255, 165, 0),   # Orange
            ],
            'text': (255, 255, 255),
            'selected_text': (255, 0, 0),  # Red text for selected territories
            'selected_border': (255, 255, 0),  # Yellow border for selected territories
            'highlight': (255, 255, 100),
            'summary_bg': (40, 40, 60),
            'summary_border': (80, 80, 120),
        }
        
        # Font for text rendering
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.large_font = pygame.font.Font(None, 32)
        
        # Generate board if territories don't exist
        if not self.game_state.territories:
            generate_sample_board(self.game_state, self.width, self.height - 120)
    
    def draw_board(self, delta_time: float = 0.0) -> None:
        """
        Draw the complete Risk board. Renders territories, continent labels, 
        player summaries, legend, and turn UI.
        
        :param delta_time: Time elapsed since last frame in seconds for 
                          animation updates
        """
        self._draw_territories()
        self._draw_continent_labels()
        self._draw_player_summaries()
        self._draw_legend()
        
        # Draw turn UI
        self.turn_ui.set_turn_state(self.turn_state)
        self.ui_renderer.draw_turn_ui(self.turn_ui)
        
        # Update and draw animations with delta time
        self.animation_manager.update_animations(delta_time)
        self._draw_animations()
    
    def set_turn_state(self, turn_state: Optional[TurnState]) -> None:
        """
        Update the renderer with new turn state.
        
        :param turn_state: Current TurnState or None if no active turn
        """
        self.turn_state = turn_state
        self.turn_ui.set_turn_state(turn_state)
    
    def get_turn_ui(self) -> TurnUI:
        """
        Get the turn UI manager.
        
        :returns: TurnUI instance for interaction handling
        """
        return self.turn_ui
    
    def start_attack_arrow_animation(self, attacker_territory_id: int, 
                                   defender_territory_id: int,
                                   player_id: int,
                                   duration: float = 1.2) -> None:
        """
        Start an arrow animation from attacking territory to defending 
        territory. Creates visual feedback for combat actions with player 
        color matching.
        
        :param attacker_territory_id: ID of attacking territory
        :param defender_territory_id: ID of defending territory
        :param player_id: ID of attacking player for color matching
        :param duration: Animation duration in seconds
        """
        attacker = self.game_state.get_territory(attacker_territory_id)
        defender = self.game_state.get_territory(defender_territory_id)
        
        if attacker and defender:
            # Get player color based on player ID
            if player_id < len(self.colors['player_colors']):
                arrow_color = self.colors['player_colors'][player_id]
            else:
                # Fallback to red if player ID exceeds available colors
                arrow_color = (255, 80, 80)
            
            self.animation_manager.add_arrow_animation(
                start_pos=attacker.center,
                end_pos=defender.center,
                duration=duration,
                color=arrow_color
            )
    
    def clear_animations(self) -> None:
        """
        Clear all active animations. Useful for game resets or state changes.
        """
        self.animation_manager.clear_all_animations()
    
    def start_movement_animation(self, source_territory_id: int, 
                               target_territory_id: int,
                               duration: float = 1.5) -> None:
        """
        Start a random walk animation for troop movement between territories.
        
        :param source_territory_id: ID of source territory
        :param target_territory_id: ID of target territory
        :param duration: Animation duration in seconds
        """
        source_territory = self.game_state.get_territory(source_territory_id)
        target_territory = self.game_state.get_territory(target_territory_id)
        
        if source_territory and target_territory:
            self.animation_manager.add_random_walk_animation(
                start_pos=source_territory.center,
                end_pos=target_territory.center,
                duration=duration
            )
    
    def start_attack_success_animation(self, territory_id: int, 
                                     player_id: int,
                                     arrow_duration: float = 1.2) -> None:
        """
        Start a tick animation at a territory to indicate successful attack. 
        Displays green checkmark for conquered territory after arrow completes.
        
        :param territory_id: ID of conquered territory
        :param player_id: ID of attacking player
        :param arrow_duration: Duration of arrow animation for timing delay
        """
        territory = self.game_state.get_territory(territory_id)
        if not territory:
            return
        
        # Get player color based on player ID
        if player_id < len(self.colors['player_colors']):
            player_color = self.colors['player_colors'][player_id]
        else:
            # Fallback to green if player ID exceeds available colors
            player_color = (0, 200, 0)
        
        self.animation_manager.add_tick_animation(
            position=territory.center,
            duration=2.0,
            delay=arrow_duration,  # Wait for arrow to reach destination
            color=player_color  # Use attacker's color
        )
    
    def start_attack_failure_animation(self, territory_id: int, 
                                     player_id: int,
                                     arrow_duration: float = 1.2) -> None:
        """
        Start a cross animation at a territory to indicate failed attack. 
        Displays red X symbol for defended territory after arrow completes.
        
        :param territory_id: ID of defended territory
        :param player_id: ID of attacking player
        :param arrow_duration: Duration of arrow animation for timing delay
        """
        territory = self.game_state.get_territory(territory_id)
        if not territory:
            return
        
        # Get player color based on player ID
        if player_id < len(self.colors['player_colors']):
            player_color = self.colors['player_colors'][player_id]
        else:
            # Fallback to red if player ID exceeds available colors
            player_color = (200, 0, 0)
        
        self.animation_manager.add_cross_animation(
            position=territory.center,
            duration=2.0,
            delay=arrow_duration,  # Wait for arrow to reach destination
            color=player_color  # Use attacker's color
        )
    
    def _draw_animations(self) -> None:
        """
        Draw all visible animations using the AnimationManager's centralized 
        rendering approach. Delegates to AnimationManager.render() for 
        optimized single-surface batch rendering.
        """
        if not self.animation_manager:
            return
        
        # Use AnimationManager's centralized rendering
        self.animation_manager.render(self.screen)
    
    def _draw_territories(self) -> None:
        """
        Draw all territories with their borders, colors, and armies. Renders 
        filled polygons, borders, and army counts.
        """
        selected_territories = []  # Keep track of selected territories for last
        
        # First pass: Draw all filled polygons
        for territory in self.game_state.territories.values():
            # Choose color based on territory state and owner
            if territory.state == TerritoryState.FREE:
                fill_color = self.colors['territory_fill']
            elif territory.state == TerritoryState.CONTESTED:
                # Contested territories get a special highlight
                if (territory.owner is not None and 
                    territory.owner < len(self.colors['player_colors'])):
                    base_color = self.colors['player_colors'][territory.owner]
                else:
                    base_color = self.colors['territory_fill']
                # Brighten the color
                fill_color = tuple(min(255, c + 50) for c in base_color)
            elif (territory.owner is not None and 
                  territory.owner < len(self.colors['player_colors'])):
                fill_color = self.colors['player_colors'][territory.owner]
            else:
                fill_color = self.colors['territory_fill']
            
            # Draw filled polygon
            if len(territory.vertices) >= 3:
                pygame.draw.polygon(self.screen, fill_color, territory.vertices)
            
            # Keep track of selected territories for later rendering
            if territory.selected:
                selected_territories.append(territory)
        
        # Second pass: Draw all non-selected territory borders
        for territory in self.game_state.territories.values():
            if not territory.selected and len(territory.vertices) >= 3:
                # Determine border color and width for non-selected territories
                if territory.state == TerritoryState.CONTESTED:
                    # Contested territories get highlight color
                    border_color = self.colors['highlight']
                    border_width = 3
                else:
                    # Normal territories get standard border
                    border_color = self.colors['territory_border']
                    border_width = 2
                
                pygame.draw.polygon(self.screen, border_color, territory.vertices, border_width)
        
        # Third pass: Draw selected territory borders (on top of everything)
        for territory in selected_territories:
            if len(territory.vertices) >= 3:
                # Selected territories get yellow outline with thicker border
                border_color = self.colors['selected_border']
                border_width = 4
                pygame.draw.polygon(self.screen, border_color, territory.vertices, border_width)
        
        # Fourth pass: Draw territory names and army counts
        for territory in self.game_state.territories.values():
            # Draw territory name with appropriate text color
            text_color = self.colors['selected_text'] if territory.selected else self.colors['text']
            text = self.small_font.render(territory.name, True, text_color)
            text_rect = text.get_rect(center=territory.center)
            self.screen.blit(text, text_rect)
            
            # Draw army count if > 0
            if territory.armies > 0:
                army_text = str(territory.armies)
                army_surface = self.font.render(army_text, True, 
                                               self.colors['text'])
                army_rect = army_surface.get_rect()
                army_rect.center = (territory.center[0], 
                                   territory.center[1] + 20)
                
                # Draw circle background for army count
                circle_color = (0, 0, 0) if (territory.state != 
                                            TerritoryState.CONTESTED) else (50, 50, 0)
                pygame.draw.circle(self.screen, circle_color, 
                                 army_rect.center, 15)
                pygame.draw.circle(self.screen, self.colors['text'], 
                                 army_rect.center, 15, 2)
                self.screen.blit(army_surface, army_rect)
    
    def _draw_continent_labels(self) -> None:
        """
        Draw continent labels and borders.
        """
        # Group territories by continent
        continents: Dict[str, List[Territory]] = {}
        for territory in self.game_state.territories.values():
            if territory.continent not in continents:
                continents[territory.continent] = []
            continents[territory.continent].append(territory)
        
        # Draw continent labels
        for continent_name, territories in continents.items():
            if not territories:
                continue
                
            # Find center of continent
            avg_x = sum(t.center[0] for t in territories) / len(territories)
            avg_y = sum(t.center[1] for t in territories) / len(territories)
            
            # Draw continent name at the top
            continent_text = self.font.render(continent_name, True, self.colors['highlight'])
            continent_rect = continent_text.get_rect()
            continent_rect.center = (int(avg_x), int(avg_y - 80))
            
            # Draw background for continent label
            padding = 5
            bg_rect = continent_rect.inflate(padding * 2, padding * 2)
            pygame.draw.rect(self.screen, (0, 0, 0, 128), bg_rect)
            pygame.draw.rect(self.screen, self.colors['highlight'], bg_rect, 2)
            
            self.screen.blit(continent_text, continent_rect)
    
    def _draw_player_summaries(self) -> None:
        """
        Draw player summary boxes along the left-hand side of the screen.
        """
        summary_width = 180
        summary_x = 10
        
        # Calculate box dimensions for vertical stacking
        box_height = 80
        box_spacing = 15
        start_y = 50  # Start below the legend area
        
        for i, player in enumerate(self.game_state.players.values()):
            # Calculate box position
            box_x = summary_x
            box_y = start_y + i * (box_height + box_spacing)
            box_w = summary_width
            box_h = box_height
            
            # Player color
            player_color = (player.color if hasattr(player, 'color') 
                           else self.colors['player_colors'][player.id % len(self.colors['player_colors'])])
            
            # Draw player box background with player's color
            box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
            pygame.draw.rect(self.screen, player_color, box_rect)
            pygame.draw.rect(self.screen, self.colors['text'], box_rect, 2)
            
            # Draw semi-transparent overlay for better text readability
            overlay_surface = pygame.Surface((box_w, box_h))
            overlay_surface.set_alpha(128)  # 50% transparency
            overlay_surface.fill((0, 0, 0))
            self.screen.blit(overlay_surface, (box_x, box_y))
            
            # Draw player information
            text_x = box_x + 8
            text_y = box_y + 5
            
            # Player name
            name_text = self.font.render(player.name, True, self.colors['text'])
            self.screen.blit(name_text, (text_x, text_y))
            
            # Territory count and army size with larger, clearer numbers
            territory_count = player.get_territory_count()
            total_armies = player.total_armies
            
            # Create two-number display format
            stats_y = text_y + 25
            
            # Territories label and number
            territories_label = self.small_font.render("Territories:", True, 
                                                      self.colors['text'])
            self.screen.blit(territories_label, (text_x, stats_y))
            
            territory_num = self.large_font.render(str(territory_count), True, 
                                                  self.colors['highlight'])
            self.screen.blit(territory_num, (text_x + 85, stats_y - 2))
            
            # Armies label and number
            armies_label = self.small_font.render("Armies:", True, 
                                                 self.colors['text'])
            self.screen.blit(armies_label, (text_x, stats_y + 20))
            
            armies_num = self.large_font.render(str(total_armies), True, 
                                               self.colors['highlight'])
            self.screen.blit(armies_num, (text_x + 85, stats_y + 18))
            
            # Active status indicator in corner
            if player.is_active:
                status_indicator = pygame.Rect(box_x + box_w - 15, box_y + 5, 
                                             10, 10)
                pygame.draw.circle(self.screen, self.colors['highlight'], 
                                 status_indicator.center, 5)
    
    def _draw_legend(self) -> None:
        """
        Draw game legend and information.
        """
        legend_x = self.width - 200
        legend_y = 20
        
        # Title
        title_text = self.large_font.render("Agent Risk", True, 
                                           self.colors['highlight'])
        self.screen.blit(title_text, (legend_x, legend_y))
        
        # Game information
        y_offset = 40
        game_info = [
            f"Phase: {self.game_state.phase.value}",
            f"Turn: {self.game_state.current_turn}",
            f"Territories: {len(self.game_state.territories)}",
            f"Players: {len(self.game_state.players)}",
        ]
        
        for info in game_info:
            text = self.small_font.render(info, True, self.colors['text'])
            self.screen.blit(text, (legend_x, legend_y + y_offset))
            y_offset += 20
        
        # Current player indicator
        if self.game_state.current_player_id is not None:
            current_player = self.game_state.get_player(self.game_state.current_player_id)
            if current_player:
                y_offset += 10
                current_text = self.font.render("Current Player:", True, self.colors['highlight'])
                self.screen.blit(current_text, (legend_x, legend_y + y_offset))
                
                y_offset += 25
                player_text = self.font.render(current_player.name, True, current_player.color)
                self.screen.blit(player_text, (legend_x, legend_y + y_offset))
        
        # Instructions
        y_offset += 40
        instructions = [
            "Dynamic Risk Board",
            "Click to interact",
            "ESC to exit"
        ]
        
        for instruction in instructions:
            text = self.small_font.render(instruction, True, self.colors['text'])
            self.screen.blit(text, (legend_x, legend_y + y_offset))
            y_offset += 20
    
    def get_territory_at_position(self, pos: Tuple[int, int]) -> Optional[Territory]:
        """Get the territory at the given screen position.
        
        Args:
            pos: Screen position (x, y)
            
        Returns:
            Territory at position, or None if no territory found
        """
        from ..utils.distance import point_in_polygon_coords
        
        x, y = pos
        for territory in self.game_state.territories.values():
            # Use proper point-in-polygon detection
            if point_in_polygon_coords(x, y, territory.vertices):
                return territory
        return None