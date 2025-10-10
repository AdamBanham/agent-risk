"""
Pygame renderer for the Risk board simulation.
Handles drawing territories, armies, and game state visualization.
"""

import pygame
import math
from typing import List, Tuple, Optional, Dict

from ..state import Territory, TerritoryState, GameState, Player
from ..state.board_generator import generate_sample_board


class GameRenderer:
    """Renders the Risk board and game state using pygame."""
    
    def __init__(self, screen: pygame.Surface, game_state: GameState):
        """Initialize the renderer.
        
        Args:
            screen: Pygame surface to draw on
            game_state: GameState to render
        """
        self.screen = screen
        self.game_state = game_state
        self.width = screen.get_width()
        self.height = screen.get_height()
        
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
    
    def draw_board(self) -> None:
        """Draw the complete Risk board."""
        self._draw_territories()
        self._draw_continent_labels()
        self._draw_player_summaries()
        self._draw_legend()
    
    def _draw_territories(self) -> None:
        """Draw all territories with their borders, colors, and armies."""
        selected_territories = []  # Keep track of selected territories for last
        
        # First pass: Draw all filled polygons
        for territory in self.game_state.territories.values():
            # Choose color based on territory state and owner
            if territory.state == TerritoryState.FREE:
                fill_color = self.colors['territory_fill']
            elif territory.state == TerritoryState.CONTESTED:
                # Contested territories get a special highlight
                if territory.owner is not None and territory.owner < len(self.colors['player_colors']):
                    base_color = self.colors['player_colors'][territory.owner]
                else:
                    base_color = self.colors['territory_fill']
                fill_color = tuple(min(255, c + 50) for c in base_color)  # Brighten the color
            elif territory.owner is not None and territory.owner < len(self.colors['player_colors']):
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
                army_surface = self.font.render(army_text, True, self.colors['text'])
                army_rect = army_surface.get_rect()
                army_rect.center = (territory.center[0], territory.center[1] + 20)
                
                # Draw circle background for army count
                circle_color = (0, 0, 0) if territory.state != TerritoryState.CONTESTED else (50, 50, 0)
                pygame.draw.circle(self.screen, circle_color, army_rect.center, 15)
                pygame.draw.circle(self.screen, self.colors['text'], army_rect.center, 15, 2)
                self.screen.blit(army_surface, army_rect)
    
    def _draw_continent_labels(self) -> None:
        """Draw continent labels and borders."""
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
        """Draw player summary boxes at the bottom of the screen."""
        summary_height = 100
        summary_y = self.height - summary_height
        
        # Draw background for entire summary area
        summary_bg_rect = pygame.Rect(0, summary_y, self.width, summary_height)
        pygame.draw.rect(self.screen, self.colors['summary_bg'], summary_bg_rect)
        pygame.draw.rect(self.screen, self.colors['summary_border'], summary_bg_rect, 2)
        
        # Calculate box dimensions
        box_width = self.width // len(self.game_state.players)
        box_padding = 10
        
        for i, player in enumerate(self.game_state.players.values()):
            # Calculate box position
            box_x = i * box_width + box_padding
            box_y = summary_y + box_padding
            box_w = box_width - 2 * box_padding
            box_h = summary_height - 2 * box_padding
            
            # Player color
            player_color = player.color if hasattr(player, 'color') else self.colors['player_colors'][player.id % len(self.colors['player_colors'])]
            
            # Draw player box background
            box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
            pygame.draw.rect(self.screen, player_color, box_rect)
            pygame.draw.rect(self.screen, self.colors['text'], box_rect, 2)
            
            # Draw player information
            text_x = box_x + 10
            text_y = box_y + 5
            
            # Player name
            name_text = self.font.render(player.name, True, self.colors['text'])
            self.screen.blit(name_text, (text_x, text_y))
            
            # Territory count
            territory_count = player.get_territory_count()
            territory_text = self.small_font.render(f"Territories: {territory_count}", True, self.colors['text'])
            self.screen.blit(territory_text, (text_x, text_y + 25))
            
            # Total armies
            total_armies = player.total_armies
            armies_text = self.small_font.render(f"Total Armies: {total_armies}", True, self.colors['text'])
            self.screen.blit(armies_text, (text_x, text_y + 45))
            
            # Active status indicator
            status_text = "ACTIVE" if player.is_active else "ELIMINATED"
            status_color = self.colors['highlight'] if player.is_active else (150, 150, 150)
            status_surface = self.small_font.render(status_text, True, status_color)
            self.screen.blit(status_surface, (text_x, text_y + 65))
    
    def _draw_legend(self) -> None:
        """Draw game legend and information."""
        legend_x = self.width - 200
        legend_y = 20
        
        # Title
        title_text = self.large_font.render("Agent Risk", True, self.colors['highlight'])
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