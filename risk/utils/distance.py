from typing import Tuple,Literal, List 
from dataclasses import dataclass
import random
import math

@dataclass
class Point:
    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

def euclidean_distance(point1: Point, point2: Point) -> float:
    """Calculate the Euclidean distance between two points."""
    return ((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2) ** 0.5

def manhattan_distance(point1: Point, point2: Point) -> float:
    """Calculate the Manhattan distance between two points."""
    return abs(point1.x - point2.x) + abs(point1.y - point2.y)

DISTANCE_METHODS = {
    'euclidean': euclidean_distance,
    'manhattan': manhattan_distance,
}

def find_closest_point(
        target: Point, 
        points: List[Point], 
        method: Literal['euclidean', 'manhattan']
    ) -> Point:
    """Find the closest point from a list to the target point."""
    closest_point = min(points, key=lambda point: DISTANCE_METHODS[method](target, point))
    return closest_point

def find_farthest_point(
        target: Point, 
        points: List[Point], 
        method: Literal['euclidean', 'manhattan']
    ) -> Point:
    """Find the farthest point from a list to the target point."""
    farthest_point = max(points, key=lambda point: DISTANCE_METHODS[method](target, point))
    return farthest_point

def clean_sequence(vertices: List[Point]) -> List[Point]:
    """Simple cleanup for polygon vertices.
    
    Args:
        vertices: List of polygon vertices
        
    Returns:
        Cleaned list of vertices
    """
    if not vertices:
        return vertices
    
    # Remove consecutive duplicates and
    # super close points
    keeping = [0, len(vertices) - 1]
    for left,right in zip(range(len(vertices)), range(1, len(vertices))):
        p1 = vertices[left]
        p2 = vertices[right]
        if euclidean_distance(p1, p2) > 1e-5:
            keeping.append(right)

    cleaned = [ vertices[i] for i in sorted(set(keeping)) ]
    # Remove last vertex if it's the same as first
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    
    return cleaned

def random_walk(
        start: Point, 
        end: Point,
        num_steps: int = 5,
        variation_strength: float = 0.2,
        clean: bool = True
    ) -> List[Point]:
    """Generate a random walk path between two points.
    
    :param start: Starting point 
    :param end: Ending point 
    :param num_steps: Number of intermediate steps in the walk
    :param variation_strength: How much the walk can deviate (0.0 = straight
    line, 1.0 = high variation)

    :return:
      List of points forming the random walk from start to end (inclusive)
    """
    if num_steps <= 0:
        return [start, end]
    
    # Calculate the direct path
    dx = end.x - start.x
    dy = end.y - start.y
    path_length = math.sqrt(dx * dx + dy * dy)
    
    # Calculate perpendicular vector for random variation
    if path_length > 0:
        # Normalized perpendicular vector
        perp_x = -dy / path_length
        perp_y = dx / path_length
    else:
        perp_x, perp_y = 0, 0
    
    # Maximum deviation distance
    max_deviation = path_length * variation_strength
    
    points = [start]
    
    # Generate intermediate points with random walk
    for i in range(1, num_steps + 1):
        # Linear interpolation factor
        t = i / (num_steps + 1)
        
        # Base position along straight line
        base_x = start.x + t * dx
        base_y = start.y + t * dy

        # Random deviation perpendicular to the line
        deviation = random.uniform(-max_deviation, max_deviation)
        
        # Add some brownian motion (correlation with previous step)
        if len(points) > 1:
            # Get previous deviation
            prev_base_x = start.x + ((i-1) / (num_steps + 1)) * dx
            prev_base_y = start.y + ((i-1) / (num_steps + 1)) * dy
            prev_deviation_x = points[-1].x - prev_base_x
            prev_deviation_y = points[-1].y - prev_base_y
            prev_deviation = (prev_deviation_x * perp_x + prev_deviation_y * perp_y)
            
            # Add correlation to previous step (brownian motion)
            correlation = 0.3
            deviation = deviation * (1 - correlation) + prev_deviation * correlation
        
        # Apply perpendicular deviation
        varied_x = base_x + deviation * perp_x
        varied_y = base_y + deviation * perp_y
        
        # Add some additional small random noise
        noise_strength = max_deviation * 0.1
        varied_x += random.uniform(-noise_strength, noise_strength)
        varied_y += random.uniform(-noise_strength, noise_strength)

        points.append(Point(varied_x, varied_y))

    # Add end point
    points.append(end)
    
    if clean:
        points = clean_sequence(points)

    return points
