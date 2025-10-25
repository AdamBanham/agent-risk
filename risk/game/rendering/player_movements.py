from ..rendering import Renderer
from ...state.game_state import GameState
from ...state.turn_manager import TurnPhase
from pygame.surface import Surface
import pygame
import math


class PlayerMovementRenderer(Renderer):
    """
    Handles showing a dashed line from the src and tgt of a movement in a
    human player's turn.
    """

    def __init__(self):
        super().__init__()

    def render(self, game_state: GameState, surface: Surface) -> None:
        """
        Render the newest state of the renderer responsibility.
        """
        manager = game_state.ui_turn_manager
        curr_turn = manager.current_turn
        player = game_state.get_player(game_state.current_player_id)

        if player and player.is_human:
            if curr_turn and curr_turn.phase == TurnPhase.MOVING:
                movement = curr_turn.current_movement
                if movement:
                    # Get source and target territories
                    src_territory = game_state.territories.get(
                        movement.source_territory_id
                    )
                    tgt_territory = game_state.territories.get(
                        movement.target_territory_id
                    )

                    if src_territory and tgt_territory:
                        # Draw a dashed gray arc between territory centers
                        src_center = src_territory.center
                        tgt_center = tgt_territory.center
                        self._draw_dashed_arc(
                            surface,
                            src_center,
                            tgt_center,
                            (128, 128, 128, 128),
                            6,
                            4,
                            10,
                        )

    def _draw_dashed_arc(
        self,
        surface: Surface,
        start: tuple,
        end: tuple,
        color: tuple,
        width: int,
        dash_length: int,
        gap_length: int,
    ) -> None:
        """
        Draw a dashed arc between two points with transparency.

        :param surface: Pygame surface to draw on
        :param start: Starting point (x, y)
        :param end: Ending point (x, y)
        :param color: RGBA color tuple for the line (with alpha)
        :param width: Line thickness in pixels
        :param dash_length: Length of each dash segment
        :param gap_length: Length of each gap between dashes
        """
        x1, y1 = start
        x2, y2 = end

        # Calculate midpoint and arc parameters
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Calculate distance and perpendicular offset for arc
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return

        # Create arc by offsetting midpoint perpendicular to the line
        # Arc height is proportional to distance (about 15% of distance)
        arc_height = distance * 0.3

        # Calculate perpendicular direction (rotate 90 degrees)
        perp_x = -dy / distance
        perp_y = dx / distance

        # Arc control point (offset midpoint)
        arc_x = mid_x + perp_x * arc_height
        arc_y = mid_y + perp_y * arc_height

        # Generate points along the quadratic bezier curve
        arc_points = self._generate_bezier_points(
            (x1, y1), (arc_x, arc_y), (x2, y2), 50
        )

        # Create temporary surface for alpha blending
        temp_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # Draw dashed line along the arc points
        self._draw_dashed_path(
            temp_surface, arc_points, color[:3], width, dash_length, gap_length
        )

        # Apply transparency and blit to main surface
        temp_surface.set_alpha(200)
        surface.blit(temp_surface, (0, 0))

    def _generate_bezier_points(
        self, p0: tuple, p1: tuple, p2: tuple, num_points: int
    ) -> list:
        """
        Generate points along a quadratic Bezier curve.

        :param p0: Start point (x, y)
        :param p1: Control point (x, y)
        :param p2: End point (x, y)
        :param num_points: Number of points to generate along the curve
        :returns: List of (x, y) points along the curve
        """
        points = []
        for i in range(num_points + 1):
            t = i / num_points

            # Quadratic Bezier formula: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]

            points.append((x, y))

        return points

    def _draw_dashed_path(
        self,
        surface: Surface,
        points: list,
        color: tuple,
        width: int,
        dash_length: int,
        gap_length: int,
    ) -> None:
        """
        Draw a dashed line along a path of points.

        :param surface: Pygame surface to draw on
        :param points: List of (x, y) points defining the path
        :param color: RGB color tuple for the line
        :param width: Line thickness in pixels
        :param dash_length: Length of each dash segment
        :param gap_length: Length of each gap between dashes
        """
        if len(points) < 2:
            return

        # Calculate cumulative distances along the path
        cumulative_distance = 0
        cycle_length = dash_length + gap_length

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]

            segment_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            # Check if we should draw this segment (in dash, not gap)
            position_in_cycle = cumulative_distance % cycle_length

            if position_in_cycle < dash_length:
                # We're in a dash segment, draw the line
                pygame.draw.line(
                    surface, color, (int(x1), int(y1)), (int(x2), int(y2)), width
                )

            cumulative_distance += segment_length
