
from pygame.surface import Surface
import pygame

from risk.state.game_state import GameState
from risk.state.event_stack import EventStack
from ..rendering import Renderer

class StackRenderer(Renderer):
    """
    This rendering the current simulation event stack.
    """

    def __init__(self, stack: EventStack):
        super().__init__()
        self.stack = stack
        self.el_height = 30
        self.el_width = 350

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
        margin = 20
        x_pos = surface.get_width() - self.el_width - margin
        
        # Start from bottom and work upward (stack grows upward)
        box_spacing = 5
        start_y = surface.get_height() - 120 - margin - self.el_height
        
        # Render each stack element as a box (top of stack appears at bottom)
        elements = []
        while not stack.is_empty:
            elements.append((stack.depth, stack.pop()))

        for i, (depth, element) in enumerate(reversed(elements)):
            new_y = int(start_y - (i * (self.el_height + box_spacing)))
            new_x = x_pos + (depth * 10)  # Indent based on depth
            
            # Skip rendering if box would be off-screen
            if new_y < 0:
                break
            
            # Add border for better visual separation
            pygame.draw.rect(surface, (255, 255, 255), 
                           (new_x, new_y, surface.get_width() // 2, self.el_height))

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
