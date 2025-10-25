"""
UI renderer for turn-based UI elements.
Handles drawing of buttons, labels, counters, and popups with consistent styling.
"""

import pygame

from ..state.ui import TurnUI, Button, Label, Counter, AttackPopup
from ..state.turn_manager import TurnPhase


class UIRenderer:
    """Renders turn-based UI elements using pygame."""

    def __init__(self, screen: pygame.Surface):
        """
        Initialize UI renderer.

        :param screen: Pygame surface to draw UI elements on
        """
        self.screen = screen

        # Initialize fonts
        pygame.font.init()
        self.fonts = {
            16: pygame.font.Font(None, 16),
            18: pygame.font.Font(None, 18),
            20: pygame.font.Font(None, 20),
            24: pygame.font.Font(None, 24),
            32: pygame.font.Font(None, 32),
        }

        # UI colors
        self.colors = {
            "panel_bg": (30, 40, 60),
            "panel_border": (80, 80, 120),
            "button_bg": (60, 80, 100),
            "button_hover": (80, 100, 120),
            "button_disabled": (40, 40, 40),
            "button_border": (100, 120, 140),
            "text": (255, 255, 255),
            "text_disabled": (150, 150, 150),
            "popup_bg": (40, 40, 60),
            "popup_border": (100, 100, 120),
            "counter_bg": (50, 60, 80),
            "counter_border": (80, 100, 120),
        }

    def draw_turn_ui(self, turn_ui: TurnUI) -> None:
        """
        Draw the complete turn UI.

        :param turn_ui: TurnUI object containing all UI state and elements
        """
        if not turn_ui.current_turn:
            # Draw minimal UI when no turn is active
            self._draw_no_turn_ui(turn_ui)
            return

        # Draw main UI panel
        self._draw_ui_panel(turn_ui)

        # Draw phase-specific elements
        self._draw_phase_label(turn_ui.phase_label)

        if turn_ui.current_turn.phase == TurnPhase.PLACEMENT:
            self._draw_placement_ui(turn_ui)
        elif turn_ui.current_turn.phase == TurnPhase.ATTACKING:
            self._draw_attacking_ui(turn_ui)
        elif turn_ui.current_turn.phase == TurnPhase.MOVING:
            self._draw_moving_ui(turn_ui)

        # Draw common buttons
        self._draw_action_buttons(turn_ui)

        # Draw attack popup if visible
        if turn_ui.attack_popup.visible:
            self._draw_attack_popup(turn_ui.attack_popup)

    def _draw_no_turn_ui(self, turn_ui: TurnUI) -> None:
        """
        Draw minimal UI when no turn is active.

        :param turn_ui: TurnUI object for positioning
        """
        # Draw UI panel background
        panel_rect = turn_ui.get_ui_rect()
        pygame.draw.rect(self.screen, self.colors["panel_bg"], panel_rect)
        pygame.draw.rect(self.screen, self.colors["panel_border"], panel_rect, 2)

        # Draw "No Active Turn" message
        font = self.fonts[24]
        text = font.render("No Active Turn", True, self.colors["text"])
        text_rect = text.get_rect()
        text_rect.center = panel_rect.center
        self.screen.blit(text, text_rect)

    def _draw_ui_panel(self, turn_ui: TurnUI) -> None:
        """
        Draw the main UI panel background.

        :param turn_ui: TurnUI object for dimensions
        """
        panel_rect = turn_ui.get_ui_rect()
        pygame.draw.rect(self.screen, self.colors["panel_bg"], panel_rect)
        pygame.draw.rect(self.screen, self.colors["panel_border"], panel_rect, 2)

    def _draw_phase_label(self, label: Label) -> None:
        """
        Draw phase label.

        :param label: Label element to draw
        """
        if not label.visible:
            return

        font = self.fonts[label.font_size]
        text_surface = font.render(label.text, True, label.text_color)

        if label.background_color:
            # Draw background if specified
            bg_rect = pygame.Rect(label.x, label.y, label.width, label.height)
            pygame.draw.rect(self.screen, label.background_color, bg_rect)

        # Position text
        if label.center_text:
            text_rect = text_surface.get_rect()
            text_rect.center = (label.x + label.width // 2, label.y + label.height // 2)
            self.screen.blit(text_surface, text_rect)
        else:
            self.screen.blit(text_surface, (label.x, label.y))

    def _draw_placement_ui(self, turn_ui: TurnUI) -> None:
        """
        Draw placement phase UI elements.

        :param turn_ui: TurnUI object containing placement elements
        """
        # Draw reinforcement counter
        if turn_ui.reinforcement_counter.visible:
            self._draw_label(turn_ui.reinforcement_counter)

        # Draw undo button
        if turn_ui.undo_button.visible:
            self._draw_button(turn_ui.undo_button)

    def _draw_attacking_ui(self, turn_ui: TurnUI) -> None:
        """
        Draw attacking phase UI elements.

        :param turn_ui: TurnUI object containing attacking elements
        """
        # Most attacking UI is handled by the attack popup
        # Any additional attacking phase UI would go here
        pass

    def _draw_moving_ui(self, turn_ui: TurnUI) -> None:
        """
        Draw moving phase UI elements.

        :param turn_ui: TurnUI object containing moving elements
        """
        # Draw movement counter if visible
        if turn_ui.movement_counter.visible:
            self._draw_counter(turn_ui.movement_counter)

        # Draw execute movement button
        if turn_ui.execute_movement_button.visible:
            self._draw_button(turn_ui.execute_movement_button)

        # draw cancel movement button
        if turn_ui.cancel_movement_button.visible:
            self._draw_button(turn_ui.cancel_movement_button)

    def _draw_action_buttons(self, turn_ui: TurnUI) -> None:
        """
        Draw common action buttons.

        :param turn_ui: TurnUI object containing action buttons
        """
        buttons = [turn_ui.advance_phase_button, turn_ui.end_turn_button]

        for button in buttons:
            if button.visible:
                self._draw_button(button)

    def _draw_button(self, button: Button) -> None:
        """
        Draw a button with text and styling.

        :param button: Button element to draw
        """
        if not button.visible:
            return

        # Get button rect
        rect = button.get_rect()

        # Choose colors based on state
        bg_color = button.get_current_background_color()
        text_color = (
            self.colors["text_disabled"] if not button.enabled else button.text_color
        )

        # Draw button background
        pygame.draw.rect(self.screen, bg_color, rect)
        pygame.draw.rect(self.screen, self.colors["button_border"], rect, 2)

        # Draw button text
        font = self.fonts[button.font_size]
        text_surface = font.render(button.text, True, text_color)
        text_rect = text_surface.get_rect()
        text_rect.center = rect.center
        self.screen.blit(text_surface, text_rect)

    def _draw_label(self, label: Label) -> None:
        """
        Draw a text label.

        :param label: Label element to draw
        """
        if not label.visible:
            return

        font = self.fonts[label.font_size]
        text_surface = font.render(label.text, True, label.text_color)

        # Draw background if specified
        if label.background_color:
            bg_rect = pygame.Rect(label.x, label.y, label.width, label.height)
            pygame.draw.rect(self.screen, label.background_color, bg_rect)

        # Position text
        if label.center_text:
            text_rect = text_surface.get_rect()
            text_rect.center = (label.x + label.width // 2, label.y + label.height // 2)
            self.screen.blit(text_surface, text_rect)
        else:
            self.screen.blit(text_surface, (label.x, label.y))

    def _draw_counter(self, counter: Counter) -> None:
        """
        Draw a counter with +/- buttons.

        :param counter: Counter element to draw
        """
        if not counter.visible:
            return

        # Draw counter background
        rect = pygame.Rect(counter.x, counter.y, counter.width, counter.height)
        pygame.draw.rect(self.screen, self.colors["counter_bg"], rect)
        pygame.draw.rect(self.screen, self.colors["counter_border"], rect, 2)

        # Draw label
        font = self.fonts[counter.font_size]
        label_text = f"{counter.label} {counter.value}"
        text_surface = font.render(label_text, True, counter.text_color)
        self.screen.blit(text_surface, (counter.x + 5, counter.y + 5))

        # Draw +/- buttons
        button_size = 25

        # Plus button
        plus_rect = pygame.Rect(
            counter.x + counter.width - 60, counter.y, button_size, button_size
        )
        pygame.draw.rect(self.screen, self.colors["button_bg"], plus_rect)
        pygame.draw.rect(self.screen, self.colors["button_border"], plus_rect, 1)

        plus_text = font.render("+", True, self.colors["text"])
        plus_text_rect = plus_text.get_rect()
        plus_text_rect.center = plus_rect.center
        self.screen.blit(plus_text, plus_text_rect)

        # Minus button
        minus_rect = pygame.Rect(
            counter.x + counter.width - 30, counter.y, button_size, button_size
        )
        pygame.draw.rect(self.screen, self.colors["button_bg"], minus_rect)
        pygame.draw.rect(self.screen, self.colors["button_border"], minus_rect, 1)

        minus_text = font.render("-", True, self.colors["text"])
        minus_text_rect = minus_text.get_rect()
        minus_text_rect.center = minus_rect.center
        self.screen.blit(minus_text, minus_text_rect)

    def _draw_attack_popup(self, popup: AttackPopup) -> None:
        """
        Draw the attack popup dialog.

        :param popup: AttackPopup to draw
        """
        if not popup.visible or not popup.attack_state:
            return

        # Draw popup background
        popup_rect = popup.get_rect()
        pygame.draw.rect(self.screen, self.colors["popup_bg"], popup_rect)
        pygame.draw.rect(self.screen, self.colors["popup_border"], popup_rect, 3)

        # Draw title
        font = self.fonts[24]
        title_text = font.render("Attack!", True, self.colors["text"])
        title_rect = title_text.get_rect()
        title_rect.centerx = popup_rect.centerx
        title_rect.y = popup_rect.y + 20
        self.screen.blit(title_text, title_rect)

        # Draw attack information
        font = self.fonts[18]
        y_offset = 60

        # Attacker info
        attacker_text = (
            f"Attacking with up to {popup.attack_state.max_attacking_armies} armies"
        )
        attacker_surface = font.render(attacker_text, True, self.colors["text"])
        self.screen.blit(attacker_surface, (popup.x + 20, popup.y + y_offset))
        y_offset += 25

        # Defender info
        defender_text = f"Defending with {popup.attack_state.defending_armies} armies"
        defender_surface = font.render(defender_text, True, self.colors["text"])
        self.screen.blit(defender_surface, (popup.x + 20, popup.y + y_offset))
        y_offset += 25

        # Current attack size
        current_text = f"Current attack size: {popup.attack_state.attacking_armies}"
        current_surface = font.render(current_text, True, self.colors["text"])
        self.screen.blit(current_surface, (popup.x + 20, popup.y + y_offset))
        y_offset += 35

        # Draw army selection counter
        self._draw_army_selector(popup)

        # Draw action buttons
        for element in popup.get_ui_elements():
            if isinstance(element, Button):
                self._draw_button(element)

    def _draw_army_selector(self, popup: AttackPopup) -> None:
        """
        Draw army selection UI in attack popup.

        :param popup: AttackPopup containing army selection state
        """
        if not popup.attack_state:
            return

        # Draw army selector background
        selector_rect = pygame.Rect(
            popup.x + 20, popup.y + popup.height - 140, popup.width - 40, 40
        )
        pygame.draw.rect(self.screen, self.colors["counter_bg"], selector_rect)
        pygame.draw.rect(self.screen, self.colors["counter_border"], selector_rect, 2)

        # Draw label and current value
        font = self.fonts[18]
        text = f"Attacking Armies: {popup.attack_state.attacking_armies}"
        text_surface = font.render(text, True, self.colors["text"])
        self.screen.blit(text_surface, (selector_rect.x + 10, selector_rect.y + 10))

        # Draw army selection buttons (1, 2, 3... up to max)
        button_width = 30
        button_height = 25
        button_spacing = 35
        start_x = popup.x + 20
        start_y = popup.y + popup.height - 95

        for i in range(1, min(popup.attack_state.max_attacking_armies + 1, 6)):
            button_rect = pygame.Rect(
                start_x + (i - 1) * button_spacing, start_y, button_width, button_height
            )

            # Highlight current selection
            if i == popup.attack_state.attacking_armies:
                bg_color = self.colors["button_hover"]
            else:
                bg_color = self.colors["button_bg"]

            pygame.draw.rect(self.screen, bg_color, button_rect)
            pygame.draw.rect(self.screen, self.colors["button_border"], button_rect, 1)

            # Draw number
            num_text = font.render(str(i), True, self.colors["text"])
            num_rect = num_text.get_rect()
            num_rect.center = button_rect.center
            self.screen.blit(num_text, num_rect)

        # If more than 5 armies available, show +/- buttons
        if popup.attack_state.max_attacking_armies > 5:
            # Plus button
            plus_rect = pygame.Rect(
                start_x + 5 * button_spacing, start_y, button_width, button_height
            )
            pygame.draw.rect(self.screen, self.colors["button_bg"], plus_rect)
            pygame.draw.rect(self.screen, self.colors["button_border"], plus_rect, 1)

            plus_text = font.render("+", True, self.colors["text"])
            plus_text_rect = plus_text.get_rect()
            plus_text_rect.center = plus_rect.center
            self.screen.blit(plus_text, plus_text_rect)

            # Minus button
            minus_rect = pygame.Rect(
                start_x + 6 * button_spacing, start_y, button_width, button_height
            )
            pygame.draw.rect(self.screen, self.colors["button_bg"], minus_rect)
            pygame.draw.rect(self.screen, self.colors["button_border"], minus_rect, 1)

            minus_text = font.render("-", True, self.colors["text"])
            minus_text_rect = minus_text.get_rect()
            minus_text_rect.center = minus_rect.center
            self.screen.blit(minus_text, minus_text_rect)
