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

def compute_bounding_box(polygon: List[Point]) -> Tuple[float, float, 
                                                        float, float]:
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
    Compute the geometric median (Fermat point) of a polygon using numerical 
    optimization. Finds the point that minimizes the sum of distances to all 
    vertices.
    
    :param polygon: List of Point objects representing the polygon vertices 
                   in order
    :returns: Point representing the geometric median centroid of the polygon
    """
    if len(polygon) == 1:
        return polygon[0]
    
    # Start with arithmetic mean as initial guess
    cx_init = sum(point.x for point in polygon) / len(polygon)
    cy_init = sum(point.y for point in polygon) / len(polygon)
    
    # Iterative Weiszfeld algorithm to find geometric median
    x, y = cx_init, cy_init
    tolerance = 1e-7
    max_iterations = 100
    
    broke = False
    for iter in range(max_iterations):
        # Calculate weighted sum using inverse distances
        numerator_x = 0.0
        numerator_y = 0.0
        denominator = 0.0
        
        for point in polygon:
            distance = ((x - point.x) ** 2 + (y - point.y) ** 2) ** 0.5
            if distance < tolerance:  # Avoid division by zero
                return Point(x, y)
            
            weight = 1.0 / distance
            numerator_x += weight * point.x
            numerator_y += weight * point.y
            denominator += weight
        
        new_x = numerator_x / denominator
        new_y = numerator_y / denominator
        
        # Check for convergence
        if abs(new_x - x) < tolerance and abs(new_y - y) < tolerance:
            broke = True
            break
            
        x, y = new_x, new_y
    return Point(x, y)