
from pygame.surface import Surface
import pygame

from risk.state.game_state import GameState
from risk.state.event_stack import EventStack
from risk.state.event_stack import (
    SideEffectEvent,
    PlayingEvent, GameEvent,
    Level, Event, 
    Rejected
)
from ..rendering import Renderer


colors = {
    "levels" : "#6C1A6A",
    "ends" : "#AB2525",
    "events" : "#DA8D35",
    "side_effects" : "#217A33",
    "system" : "#1B659D",
    "specials" : "#8A7E7F",
}

def swap_color(color_hex: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    color_hex = color_hex.lstrip('#')
    lv = len(color_hex)
    return tuple(int(color_hex[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

for key in colors:
    colors[key] = swap_color(colors[key])

class StackRenderer(Renderer):
    """
    This rendering the current simulation event stack.
    """

    def __init__(self, stack: EventStack):
        super().__init__()
        self.stack = stack
        self.el_height = 30
        self.el_x_margin = 15
        self.el_y_margin = 140
        self.el_indent_depth = 25
        self.el_width = 500

    def render(self, game_state: GameState, surface: Surface) -> None:
        """
        Renders the event stack as a vertical column of boxes on the right 
        side of the screen. Each box displays one stack element.
        
        :param game_state: Current game state (for consistency with Renderer 
                          interface)
        :param surface: Pygame surface to render the stack boxes onto
        """
        stack = self.stack.substack(self.stack.size)
        
        # Position boxes on the right side with margin
        x_pos = surface.get_width() - self.el_width - self.el_x_margin
        
        # Start from bottom and work upward (stack grows upward)
        box_spacing = 5
        start_y = surface.get_height() - self.el_y_margin - self.el_height
        
        # Render each stack element as a box (top of stack appears at bottom)
        elements = []
        while not stack.is_empty:
            elements.append((stack.depth, stack.pop()))

        for i, (depth, element) in enumerate(reversed(elements)):
            new_y = int(start_y - (i * (self.el_height + box_spacing)))
            indent = self.el_indent_depth * depth
            new_x = x_pos + indent  # Indent based on depth
            
            # Skip rendering if box would be off-screen
            if new_y < 0:
                break
            
            bg_color, fill_color = self._find_colors(element)
            # Add border for better visual separation
            pygame.draw.rect(surface, fill_color, 
                (new_x, new_y, self.el_width - indent, self.el_height)
            )
            pygame.draw.rect(surface, bg_color, 
                (new_x, new_y, self.el_width - indent, self.el_height),
                4
            )

            # Render element text with proper truncation
            font = pygame.font.Font(None, 16)
            element_text = str(element)
            
            # Truncate text if too long for box width
            max_text_width = self.el_width - 10  # Leave padding
            if font.size(element_text)[0] > max_text_width:
                # Truncate and add ellipsis
                while font.size(element_text + "...")[0] > max_text_width and len(element_text) > 1:
                    element_text = element_text[:-1]
                element_text += "..."
            
            text_surf = font.render(element_text, True, (0, 0, 0))
            surface.blit(text_surf, (new_x + 5, new_y + self.el_height // 2 - text_surf.get_height() // 2))

    def _find_colors(self, element: Event | Level) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Determine the foreground and background colors for a stack element."""
        if isinstance(element, Level):
            bg_color = colors["levels"]
        elif isinstance(element, (PlayingEvent, GameEvent)):
            bg_color = colors["specials"]
        elif "SYSTEM" in element.name:
            bg_color = colors["system"]
        elif "phase end" in element.name.lower():
            bg_color = colors["ends"]
        elif isinstance(element, Rejected):
            bg_color = colors["ends"]
        elif isinstance(element, SideEffectEvent):
            bg_color = colors["side_effects"]
        else:
            bg_color = colors["events"]
        
        fill_color = tuple(
            min(255, c + c * 0.25) for c in bg_color
        )
        
        return bg_color, fill_color
