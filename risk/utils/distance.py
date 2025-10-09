from typing import Tuple,Literal
from dataclasses import dataclass

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
        points: list[Point], 
        method: Literal['euclidean', 'manhattan']
    ) -> Point:
    """Find the closest point from a list to the target point."""
    closest_point = min(points, key=lambda point: DISTANCE_METHODS[method](target, point))
    return closest_point

def find_farthest_point(
        target: Point, 
        points: list[Point], 
        method: Literal['euclidean', 'manhattan']
    ) -> Point:
    """Find the farthest point from a list to the target point."""
    farthest_point = max(points, key=lambda point: DISTANCE_METHODS[method](target, point))
    return farthest_point