from .distance import Point
from typing import List, Tuple

def compute_area(polygon: List[Point]) -> float:
    """
    Compute the area of a polygon using the Shoelace formula. Uses the 
    standard shoelace (surveyor's) formula.
    
    :param polygon: List of Point objects representing the polygon vertices 
                   in order
    :returns: Area of the polygon as a positive float value
    """
    n = len(polygon)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += polygon[i].x * polygon[j].y
        area -= polygon[j].x * polygon[i].y
    area = abs(area) / 2.0
    return area

def compute_bounding_box(polygon: List[Point]) -> Tuple[float, float, float, float]:
    """
    Compute the axis-aligned bounding box of a polygon. Finds the minimum 
    rectangle that encloses all vertices.
    
    :param polygon: List of Point objects representing the polygon vertices
    :returns: Tuple (min_x, min_y, max_x, max_y) defining the bounding box
    """
    if not polygon:
        return (0, 0, 0, 0)
    
    min_x = min(point.x for point in polygon)
    max_x = max(point.x for point in polygon)
    min_y = min(point.y for point in polygon)
    max_y = max(point.y for point in polygon)
    
    return (min_x, min_y, max_x, max_y)

def find_centroid(polygon: List[Point]) -> Point:
    """
    Compute the centroid (geometric center) of a polygon. Uses the standard 
    centroid formula for polygons.
    
    :param polygon: List of Point objects representing the polygon vertices 
                   in order
    :returns: Point representing the centroid of the polygon
    """
    n = len(polygon)
    if n == 0:
        return Point(0, 0)
    
    cx = 0.0
    cy = 0.0
    area = compute_area(polygon)
    
    factor = 0.0
    for i in range(n):
        j = (i + 1) % n
        factor = (polygon[i].x * polygon[j].y - polygon[j].x * polygon[i].y)
        cx += (polygon[i].x + polygon[j].x) * factor
        cy += (polygon[i].y + polygon[j].y) * factor

    area *= 6.0
    if area == 0:
        return Point(0, 0)
    
    cx /= area
    cy /= area
    
    return Point(cx, cy)