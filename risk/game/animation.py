"""
Animation system for the Risk simulation.
Provides arrow animations for attacks, crosses for failures, and ticks for successes.
All animations use delta-time based updates with lifetime management.
"""

import time
import math
import pygame
from enum import Enum
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass

from ..utils.distance import Point, random_walk, euclidean_distance


class AnimationState(Enum):
    """Animation state enumeration for consistent state management."""
    WAITING = "waiting"     # Animation in delay phase before starting
    ACTIVE = "active"       # Animation currently running
    AFTER = "after"         # Animation in after phase (post-completion)
    COMPLETED = "completed" # Animation fully finished


class BaseAnimation:
    """
    Base class for all animations with lifetime management. Handles the common
    pattern of delay + duration + after phases using a single life_duration tracker.
    """
    
    def __init__(self, duration: float, delay: float = 0.0, after: float = 0.0):
        """
        Initialize animation with lifetime phases.
        
        :param duration: Main animation duration in seconds
        :param delay: Delay before animation starts in seconds
        :param after: After duration to keep animation visible in seconds
        """
        self.duration = duration
        self.delay = delay
        self.after = after
        self.life_duration = 0.0  # Total time animation has been alive
        self.state = AnimationState.WAITING if delay > 0 else AnimationState.ACTIVE
        self.progress = 0.0  # Progress through active animation (0.0 to 1.0)
    
    def update(self, delta_time: float) -> None:
        """
        Update animation lifetime and state transitions.
        
        :param delta_time: Time elapsed since last update in seconds
        """
        self.life_duration += delta_time
        
        if self.state == AnimationState.WAITING:
            if self.life_duration >= self.delay:
                self.state = AnimationState.ACTIVE
        elif self.state == AnimationState.ACTIVE:
            active_time = self.life_duration - self.delay
            self.progress = min(1.0, active_time / self.duration)
            if self.progress >= 1.0:
                self.state = AnimationState.AFTER if self.after > 0 else AnimationState.COMPLETED
        elif self.state == AnimationState.AFTER:
            after_time = self.life_duration - self.delay - self.duration
            if after_time >= self.after:
                self.state = AnimationState.COMPLETED
    
    def is_done(self) -> bool:
        """
        Check if animation has fully completed all phases.
        
        :returns: True if animation is completed, False otherwise
        """
        return self.state == AnimationState.COMPLETED
    
    def is_visible(self) -> bool:
        """
        Check if animation should be drawn on screen.
        
        :returns: True if animation is in active or after phase
        """
        return self.state in (AnimationState.ACTIVE, AnimationState.AFTER)


class ArrowAnimation(BaseAnimation):
    """
    Arrow animation for attack visualization. Shows movement from attacking 
    territory to defending territory with enhanced visual effects.
    """
    
    def __init__(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], 
                 duration: float, color: Tuple[int, int, int], width: int = 3, 
                 head_size: int = 8, delay: float = 0.0, after: float = 0.0):
        """
        Initialize arrow animation.
        
        :param start_pos: Starting position (x, y)
        :param end_pos: Ending position (x, y)
        :param duration: Animation duration in seconds
        :param color: RGB color tuple for arrow
        :param width: Arrow line width in pixels
        :param head_size: Arrow head size in pixels
        :param delay: Delay before animation starts
        :param after: Duration to keep arrow visible after completion
        """
        super().__init__(duration, delay, after)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.color = color
        self.width = width
        self.head_size = head_size
        
        # Calculate direction vector
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        length = math.sqrt(dx * dx + dy * dy)
        self.direction = (dx / length, dy / length) if length > 0 else (1.0, 0.0)
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render the arrow animation to the provided surface with drop shadow 
        and enhanced visual effects.
        
        :param surface: Pygame surface to draw on
        """
        if not self.is_visible():
            return
        
        current_pos = self._get_current_position()
        tail_pos = self._get_arrow_tail_position(tail_length=60.0)
        
        # Draw drop shadow first (offset by 3 pixels down and right)
        shadow_offset = 3
        shadow_current = (current_pos[0] + shadow_offset, current_pos[1] + shadow_offset)
        shadow_tail = (tail_pos[0] + shadow_offset, tail_pos[1] + shadow_offset)
        shadow_color = (30, 30, 30)  # Dark gray shadow
        
        # Draw shadow arrow line
        pygame.draw.line(
            surface,
            shadow_color,
            shadow_tail,
            shadow_current,
            max(1, self.width - 1)  # Slightly thinner shadow
        )
        
        # Draw shadow arrowhead
        self._draw_arrow_head(
            surface,
            shadow_current,
            shadow_tail,
            shadow_color,
            self.head_size
        )
        
        # Draw main arrow with enhanced color (30% darker)
        enhanced_color = self._enhance_color(self.color)
        
        # Draw main arrow line
        pygame.draw.line(
            surface,
            enhanced_color,
            tail_pos,
            current_pos,
            self.width
        )
        
        # Draw main arrowhead
        self._draw_arrow_head(
            surface,
            current_pos,
            tail_pos,
            enhanced_color,
            self.head_size
        )
    
    def _get_current_position(self) -> Tuple[float, float]:
        """
        Get current arrow tip position based on animation progress.
        
        :returns: (x, y) current position tuple
        """
        t = min(1.0, self.progress)
        x = self.start_pos[0] + t * (self.end_pos[0] - self.start_pos[0])
        y = self.start_pos[1] + t * (self.end_pos[1] - self.start_pos[1])
        return (x, y)
    
    def _get_arrow_tail_position(self, tail_length: float = 60.0) -> Tuple[float, float]:
        """
        Calculate arrow tail position for enhanced visual effect.
        
        :param tail_length: Length of arrow tail in pixels
        :returns: (x, y) tail position tuple
        """
        current_pos = self._get_current_position()
        tail_x = current_pos[0] - self.direction[0] * tail_length
        tail_y = current_pos[1] - self.direction[1] * tail_length
        return (tail_x, tail_y)
    
    @staticmethod
    def _enhance_color(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """
        Enhance arrow color by making it 30% darker for better visibility.
        
        :param color: RGB color tuple
        :returns: Enhanced color tuple
        """
        return (
            int(color[0] * 0.7),
            int(color[1] * 0.7),
            int(color[2] * 0.7)
        )
    
    @staticmethod
    def _draw_arrow_head(surface: pygame.Surface, head_pos: Tuple[float, float], 
                        tail_pos: Tuple[float, float], color: Tuple[int, int, int], 
                        head_size: int) -> None:
        """
        Draw an arrowhead at the specified position pointing in the correct 
        direction.
        
        :param surface: Pygame surface to draw on
        :param head_pos: (x, y) position for arrowhead tip
        :param tail_pos: (x, y) position for arrow tail (for direction)
        :param color: RGB color tuple for arrowhead
        :param head_size: Size of arrowhead in pixels
        """
        # Calculate direction vector
        dx = head_pos[0] - tail_pos[0]
        dy = head_pos[1] - tail_pos[1]
        length = math.sqrt(dx * dx + dy * dy)
        
        if length == 0:
            return
        
        # Normalize direction
        dx /= length
        dy /= length
        
        # Calculate perpendicular vector for arrowhead wings
        perp_x = -dy
        perp_y = dx
        
        # Calculate arrowhead points
        back_x = head_pos[0] - dx * head_size
        back_y = head_pos[1] - dy * head_size
        
        wing1_x = back_x + perp_x * head_size * 0.5
        wing1_y = back_y + perp_y * head_size * 0.5
        
        wing2_x = back_x - perp_x * head_size * 0.5
        wing2_y = back_y - perp_y * head_size * 0.5
        
        # Draw arrowhead triangle
        points = [
            (int(head_pos[0]), int(head_pos[1])),
            (int(wing1_x), int(wing1_y)),
            (int(wing2_x), int(wing2_y))
        ]
        
        # Filled triangle for arrowhead
        pygame.draw.polygon(surface, color, points)


class CrossAnimation(BaseAnimation):
    """
    Cross (X) animation for attack failure visualization. Shows floating 
    cross that appears after arrow reaches target. Uses attacker's color.
    """
    
    def __init__(self, position: Tuple[float, float], duration: float, 
                 color: Tuple[int, int, int], size: int = 20, thickness: int = 3,
                 delay: float = 0.5, after: float = 0.3):
        """
        Initialize cross animation.
        
        :param position: (x, y) position for cross center
        :param duration: Animation duration in seconds
        :param color: RGB color tuple for cross (attacker's color)
        :param size: Cross size in pixels
        :param thickness: Cross line thickness
        :param delay: Delay before animation starts
        :param after: Duration to keep cross visible after completion
        """
        super().__init__(duration, delay, after)
        self.position = position
        self.color = color
        self.size = size
        self.thickness = thickness
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render the cross animation to the provided surface with scaling 
        and enhanced visual effects using attacker's color.
        
        :param surface: Pygame surface to draw on
        """
        if not self.is_visible():
            return
        
        x, y = self._get_current_position()
        size = int(self.size * self._get_scale())
        thickness = max(1, int(self.thickness * self._get_scale()))
        
        # Draw shadow first (offset by 2 pixels)
        shadow_offset = 2
        shadow_color = (60, 60, 60)  # Gray shadow
        
        # Shadow - first diagonal (top-left to bottom-right)
        pygame.draw.line(
            surface,
            shadow_color,
            (x - size // 2 + shadow_offset, y - size // 2 + shadow_offset),
            (x + size // 2 + shadow_offset, y + size // 2 + shadow_offset),
            max(1, thickness - 1)
        )
        
        # Shadow - second diagonal (top-right to bottom-left) 
        pygame.draw.line(
            surface,
            shadow_color,
            (x + size // 2 + shadow_offset, y - size // 2 + shadow_offset),
            (x - size // 2 + shadow_offset, y + size // 2 + shadow_offset),
            max(1, thickness - 1)
        )
        
        # Draw main cross with enhanced attacker color
        enhanced_color = (
            min(255, int(self.color[0] * 1.2)),  # Brighter
            min(255, int(self.color[1] * 1.2)),  # Brighter  
            min(255, int(self.color[2] * 1.2))   # Brighter
        )
        
        # First diagonal (top-left to bottom-right)
        pygame.draw.line(
            surface,
            enhanced_color,
            (x - size // 2, y - size // 2),
            (x + size // 2, y + size // 2),
            thickness
        )
        
        # Second diagonal (top-right to bottom-left)
        pygame.draw.line(
            surface,
            enhanced_color,
            (x + size // 2, y - size // 2),
            (x - size // 2, y + size // 2),
            thickness
        )
    
    def _get_current_position(self) -> Tuple[float, float]:
        """
        Get current cross position with floating upward motion.
        
        :returns: (x, y) current position tuple
        """
        base_x, base_y = self.position
        
        if self.state == AnimationState.WAITING:
            return (base_x, base_y)
        
        # Float upward by 30 pixels during animation
        float_offset = self.progress * 30.0
        return (base_x, base_y - float_offset)
    
    def _get_scale(self) -> float:
        """
        Get current scale factor for cross size.
        
        :returns: Scale factor (0.5 to 1.2)
        """
        if self.state == AnimationState.WAITING:
            return 0.5
        
        # Scale from 0.5 to 1.2 during animation
        return 0.5 + (self.progress * 0.7)


class TickAnimation(BaseAnimation):
    """
    Tick (✓) animation for attack success visualization. Shows floating 
    tick that appears after arrow reaches target. Uses attacker's color.
    """
    
    def __init__(self, position: Tuple[float, float], duration: float, 
                 color: Tuple[int, int, int], size: int = 20, thickness: int = 3,
                 delay: float = 0.5, after: float = 0.3):
        """
        Initialize tick animation.
        
        :param position: (x, y) position for tick center
        :param duration: Animation duration in seconds
        :param color: RGB color tuple for tick (attacker's color)
        :param size: Tick size in pixels
        :param thickness: Tick line thickness
        :param delay: Delay before animation starts
        :param after: Duration to keep tick visible after completion
        """
        super().__init__(duration, delay, after)
        self.position = position
        self.color = color
        self.size = size
        self.thickness = thickness
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render the tick animation to the provided surface with scaling 
        and enhanced visual effects using attacker's color.
        
        :param surface: Pygame surface to draw on
        """
        if not self.is_visible():
            return
        
        x, y = self._get_current_position()
        size = int(self.size * self._get_scale())
        thickness = max(1, int(self.thickness * self._get_scale()))
        
        # Draw shadow first (offset by 2 pixels)
        shadow_offset = 2
        shadow_color = (60, 60, 60)  # Gray shadow
        
        # Shadow - left side of tick
        pygame.draw.line(
            surface,
            shadow_color,
            (x - size // 3 + shadow_offset, y + shadow_offset),
            (x + shadow_offset, y + size // 2 + shadow_offset),
            max(1, thickness - 1)
        )
        
        # Shadow - right side of tick
        pygame.draw.line(
            surface,
            shadow_color,
            (x + shadow_offset, y + size // 2 + shadow_offset),
            (x + size // 2 + shadow_offset, y - size // 3 + shadow_offset),
            max(1, thickness - 1)
        )
        
        # Draw main tick mark (checkmark shape) with enhanced attacker color
        enhanced_color = (
            min(255, int(self.color[0] * 1.2)),  # Brighter
            min(255, int(self.color[1] * 1.2)),  # Brighter
            min(255, int(self.color[2] * 1.2))   # Brighter
        )
        
        # Left side of tick (shorter vertical line going down-right)
        pygame.draw.line(
            surface,
            enhanced_color,
            (x - size // 3, y),
            (x, y + size // 2),
            thickness
        )
        
        # Right side of tick (longer line going up-right)
        pygame.draw.line(
            surface,
            enhanced_color,
            (x, y + size // 2),
            (x + size // 2, y - size // 3),
            thickness
        )
    
    def _get_current_position(self) -> Tuple[float, float]:
        """
        Get current tick position with floating upward motion.
        
        :returns: (x, y) current position tuple
        """
        base_x, base_y = self.position
        
        if self.state == AnimationState.WAITING:
            return (base_x, base_y)
        
        # Float upward by 30 pixels during animation
        float_offset = self.progress * 30.0
        return (base_x, base_y - float_offset)
    
    def _get_scale(self) -> float:
        """
        Get current scale factor for tick size.
        
        :returns: Scale factor (0.5 to 1.2)
        """
        if self.state == AnimationState.WAITING:
            return 0.5
        
        # Scale from 0.5 to 1.2 during animation
        return 0.5 + (self.progress * 0.7)


class RandomWalkAnimation(BaseAnimation):
    """
    Random walk animation for troop movement visualization. Shows a black line
    that follows a random walk path from source territory to destination territory.
    """
    
    def __init__(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], 
                 duration: float, width: int = 2, delay: float = 0.0, after: float = 0.2):
        """
        Initialize random walk animation.
        
        :param start_pos: Starting position (x, y) - center of source territory
        :param end_pos: Ending position (x, y) - center of destination territory
        :param duration: Animation duration in seconds
        :param width: Line width in pixels
        :param delay: Delay before animation starts
        :param after: Duration to keep path visible after completion
        """
        super().__init__(duration, delay, after)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.width = width
        
        # Generate random walk path using distance.py functions
        start_point = Point(start_pos[0], start_pos[1])
        end_point = Point(end_pos[0], end_pos[1])
        dist = euclidean_distance(start_point, end_point)
        steps = 10 + int((dist // 10) * 10)
        print("computing steps :: ", steps)
        
        # Generate random walk with moderate variation
        try :
            walk_points = random_walk(
                start=start_point,
                end=end_point,
                num_steps=steps,
                variation_strength=0.05,
                clean=True
            ) 
        except :
            walk_points = random_walk(
                start=start_point,
                end=end_point,
                num_steps=25,
                variation_strength=0.05,
                clean=True
            ) 

        print("computed_steps...", len(walk_points))
        
        # Convert to tuples for pygame
        self.path_points = [point.to_tuple() for point in walk_points]
        
        # Calculate cumulative distances for smooth progress tracking
        self.segment_distances = []
        self.total_distance = 0.0
        
        for i in range(len(self.path_points) - 1):
            p1 = Point(self.path_points[i][0], self.path_points[i][1])
            p2 = Point(self.path_points[i + 1][0], self.path_points[i + 1][1])
            distance = math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
            self.segment_distances.append(distance)
            self.total_distance += distance
        
        # Normalize segment distances to fractions of total path
        self.cumulative_fractions = [0.0]
        cumulative_distance = 0.0
        for distance in self.segment_distances:
            cumulative_distance += distance
            self.cumulative_fractions.append(cumulative_distance / self.total_distance)
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render the random walk animation showing progressive path drawing.
        
        :param surface: Pygame surface to draw on
        """
        if not self.is_visible():
            return
        
        # Draw the path progressively based on animation progress
        current_points = self._get_current_path()
        
        if len(current_points) < 2:
            return
        
        # Create temporary surface with per-pixel alpha for proper transparency
        tmp_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        # Don't set global alpha - we'll use per-pixel alpha instead
        
        # Calculate alpha value for semi-transparent effect
        alpha_value = int(255 * 0.66)  # 66% opacity
        
        # Draw shadow first (offset by 2 pixels)
        shadow_offset = 2
        shadow_color = (60, 60, 60, alpha_value)  # Gray shadow with alpha
        shadow_points = [(x + shadow_offset, y + shadow_offset) for x, y in current_points]
        
        if len(shadow_points) >= 2:
            pygame.draw.lines(
                tmp_surface,
                shadow_color,
                False,  # Not closed
                shadow_points,
                max(1, self.width - 1)
            )
        
        # Draw main path in semi-transparent black
        path_color = (20, 20, 20, alpha_value)  # Dark black with alpha
        pygame.draw.lines(
            tmp_surface,
            path_color,
            False,  # Not closed
            current_points,
            self.width
        )
        
        # Draw small circles at key points for visual enhancement
        if len(current_points) >= 2:
            # Draw start point
            pygame.draw.circle(
                tmp_surface,
                (40, 40, 40, alpha_value),
                (int(current_points[0][0]), int(current_points[0][1])),
                max(2, self.width)
            )
            
            # Draw end point if animation is complete or nearly complete
            if self.progress > 0.9:
                pygame.draw.circle(
                    tmp_surface,
                    (10, 10, 10, alpha_value),
                    (int(current_points[-1][0]), int(current_points[-1][1])),
                    max(3, self.width + 1)
                )
        
        # Blit the temporary surface to the main surface
        surface.blit(tmp_surface, (0, 0))
    
    def _get_current_path(self) -> List[Tuple[float, float]]:
        """
        Get the current visible portion of the path based on animation progress.
        
        :returns: List of (x, y) points representing current visible path
        """
        if self.progress <= 0.0:
            return [self.path_points[0]]
        
        if self.progress >= 1.0:
            return self.path_points
        
        # Find which segment we're currently in
        current_points = []
        target_fraction = self.progress
        
        for i, fraction in enumerate(self.cumulative_fractions):
            if target_fraction >= fraction:
                current_points.append(self.path_points[i])
            else:
                # Interpolate within the current segment
                if i > 0:
                    prev_fraction = self.cumulative_fractions[i - 1]
                    segment_progress = (target_fraction - prev_fraction) / (fraction - prev_fraction)
                    
                    p1 = self.path_points[i - 1]
                    p2 = self.path_points[i]
                    
                    # Linear interpolation
                    interp_x = p1[0] + segment_progress * (p2[0] - p1[0])
                    interp_y = p1[1] + segment_progress * (p2[1] - p1[1])
                    
                    current_points.append((interp_x, interp_y))
                break
        
        return current_points if current_points else [self.path_points[0]]


class AnimationManager:
    """
    Manages all active animations in the game using a single queue. Provides 
    centralized control for creating, updating, and rendering all animation types.
    """
    
    def __init__(self):
        """Initialize the animation manager with empty animation queue."""
        self.animations: List[BaseAnimation] = []
    
    def add_arrow_animation(self, start_pos: Tuple[float, float], 
                           end_pos: Tuple[float, float], duration: float,
                           color: Tuple[int, int, int]) -> ArrowAnimation:
        """
        Create and register a new arrow animation. Arrow travels from start 
        to end position over specified duration.
        
        :param start_pos: (x, y) starting position
        :param end_pos: (x, y) ending position  
        :param duration: Animation duration in seconds
        :param color: RGB color tuple for arrow (attacker's color)
        :returns: Created ArrowAnimation object for reference
        """
        animation = ArrowAnimation(
            start_pos=start_pos,
            end_pos=end_pos,
            duration=duration,
            color=color
        )
        
        self.animations.append(animation)
        return animation
    
    def add_cross_animation(self, position: Tuple[float, float], 
                           duration: float, delay: float,
                           color: Tuple[int, int, int]) -> CrossAnimation:
        """
        Create and register a new cross animation. Cross appears after delay 
        and shows attack failure.
        
        :param position: (x, y) position for cross center
        :param duration: Animation duration in seconds (after delay)
        :param delay: Delay before animation starts (arrow travel time)
        :param color: RGB color tuple for cross (attacker's color)
        :returns: Created CrossAnimation object for reference
        """
        animation = CrossAnimation(
            position=position,
            duration=duration,
            color=color,
            delay=delay
        )
        
        self.animations.append(animation)
        return animation
    
    def add_tick_animation(self, position: Tuple[float, float], 
                          duration: float, delay: float,
                          color: Tuple[int, int, int]) -> TickAnimation:
        """
        Create and register a new tick animation. Tick appears after delay 
        and shows attack success.
        
        :param position: (x, y) position for tick center
        :param duration: Animation duration in seconds (after delay)
        :param delay: Delay before animation starts (arrow travel time)
        :param color: RGB color tuple for tick (attacker's color)
        :returns: Created TickAnimation object for reference
        """
        animation = TickAnimation(
            position=position,
            duration=duration,
            color=color,
            delay=delay
        )
        
        self.animations.append(animation)
        return animation
    
    def add_random_walk_animation(self, start_pos: Tuple[float, float], 
                                 end_pos: Tuple[float, float], duration: float) -> RandomWalkAnimation:
        """
        Create and register a new random walk animation. Shows troop movement
        along a random walk path between territories.
        
        :param start_pos: (x, y) starting position (center of source territory)
        :param end_pos: (x, y) ending position (center of destination territory)
        :param duration: Animation duration in seconds
        :returns: Created RandomWalkAnimation object for reference
        """
        animation = RandomWalkAnimation(
            start_pos=start_pos,
            end_pos=end_pos,
            duration=duration
        )
        
        self.animations.append(animation)
        return animation
    
    def update_animations(self, delta_time: float) -> None:
        """
        Update all active animations and remove completed ones. Should be 
        called once per frame in game loop.
        
        :param delta_time: Time elapsed since last frame in seconds
        """
        # Update all animations
        for animation in self.animations:
            animation.update(delta_time)
        
        # Remove completed animations
        self.animations = [anim for anim in self.animations if not anim.is_done()]
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render all active animations to the provided surface using optimized 
        single-surface approach. Creates temporary surface with alpha for 
        performance.
        
        :param surface: Main pygame surface to render animations on
        """
        # Early exit if no animations to render
        if not self.animations:
            return
        
        # Create temporary surface for batch rendering with alpha
        temp_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        temp_surface.set_alpha(230)  # 10% transparency (255 * 0.9 = 230)
        
        # Render all animations to temporary surface
        for animation in self.animations:
            animation.render(temp_surface)
        
        # Blit temporary surface to main surface once
        surface.blit(temp_surface, (0, 0))
    
    def clear_all_animations(self) -> None:
        """
        Clear all active animations. Useful for game resets or pause states.
        """
        self.animations.clear()
    
    def get_animation_count(self) -> int:
        """
        Get number of active animations.
        
        :returns: Count of active animations
        """
        return len(self.animations)