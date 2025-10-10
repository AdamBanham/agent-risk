"""
Dynamic board generation for the Risk simulation.
Creates territories using polygon subdivision - starts with a large continent
and recursively divides it into smaller territories using random walk 
division lines.
"""

import math
import random
from typing import List, Tuple, Dict, Set, Optional
from .territory import Territory
from .game_state import GameState
from ..utils.distance import Point
from ..utils.distance import random_walk, clean_sequence
from ..utils.polygon import compute_area, find_centroid, compute_bounding_box
from copy import deepcopy


class PolygonTerritory:
    """Represents a territory during the subdivision process."""
    
    def __init__(self, vertices: List[Point], territory_id: int = -1):
        """
        Initialize a polygon territory. Creates a polygon territory with 
        vertices and calculates properties.
        
        :param vertices: List of Point objects or (x, y) tuples defining the 
                        polygon
        :param territory_id: Unique ID for this territory (-1 if not 
                            finalized)
        """
        self.vertices = [
            p if isinstance(p, Point) else Point(*p)
            for p in vertices
        ]
        self.territory_id = territory_id
        self._center = find_centroid(self.vertices)
        self._box = compute_bounding_box(self.vertices)
        self.is_divided = False
        self._area = compute_area(self.vertices)

    def center(self) -> Tuple[int, int]:
        """
        Calculate the centroid of the polygon. Returns the geometric center 
        as integer coordinates.
        
        :returns: Center point (x, y) as integer tuple
        """
        return self._center.to_tuple()
    
    def bounding_box(self) -> Tuple[int, int, int, int]:
        """
        Get the bounding box of this polygon. Returns the axis-aligned 
        rectangle that encloses all vertices.
        
        :returns: Tuple of (min_x, min_y, max_x, max_y) coordinates
        """
        return self._box
    
    def area(self) -> float:
        """
        Returns the area of the polygon.
        
        :returns: Area of the polygon (always positive)
        """
        return self._area
    
    def signed_area(self) -> float:
        """
        Calculate the signed area of the polygon. Positive for 
        counter-clockwise vertices, negative for clockwise.
        
        :returns: Signed area (positive for counter-clockwise, negative for 
                 clockwise)
        """
        if not self.vertices or len(self.vertices) < 3:
            return 0.0
        
        area = 0.0
        n = len(self.vertices)
        
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i].x * self.vertices[j].y
            area -= self.vertices[j].x * self.vertices[i].y

        return area / 2.0
    
    def is_clockwise(self) -> bool:
        """
        Check if vertices are ordered clockwise. Uses signed area to 
        determine vertex ordering.
        
        :returns: True if clockwise, False if counter-clockwise
        """
        return self.signed_area() < 0
    
    def divide(self) -> Tuple['PolygonTerritory', 'PolygonTerritory']:
        """
        Divide this polygon into two smaller polygons using a random walk 
        line. Uses random vertex selection and jagged division lines.
        
        :returns: Two new PolygonTerritory instances resulting from the 
                 division
        :raises ValueError: When polygon cannot be divided after multiple 
                           attempts
        """        
        left = None
        right = None
        lprop = None
        attempts = 0
        while (left is None or right is None) or (lprop < 0.3 or lprop > 0.7):
            choice = random.choice(range(len(self.vertices)))
            other = random.choice(range(len(self.vertices)))
            while choice == other and abs(choice - other) < 25:
                other = random.choice(range(len(self.vertices)))

            lpivot = self.vertices[choice]
            rpivot = self.vertices[other]


            walk = random_walk(
                lpivot, rpivot, num_steps=25, variation_strength=0.02
            )

            if choice < other:
                left = PolygonTerritory(
                self.vertices[choice+1:other] + walk[::-1]
                )
                right = PolygonTerritory(
                    self.vertices[other+1:] + self.vertices[:choice] + walk
                )
            else:
                left = PolygonTerritory(
                    self.vertices[choice+1:] + self.vertices[:other] + 
                    walk[::-1]
                )
                right = PolygonTerritory(
                    self.vertices[other+1:choice] + walk
                )
            lvalidation = left.validate_vertices()
            rvalidation = right.validate_vertices()
            if not lvalidation['is_valid'] or not rvalidation['is_valid']:
                left = None
                right = None
                continue
            sum_of_areas = left.area() + right.area()
            lprop = left.area() / sum_of_areas if sum_of_areas > 0 else 0
            if attempts > 10:
                raise ValueError("Failed to divide polygon into two valid "
                               "parts after multiple attempts.")
        self.is_divided = True
        return left, right


    def is_valid(self) -> bool:
        """
        Check if the polygon is valid (at least 3 vertices and non-zero 
        area). Basic validity check for polygon geometry.
        
        :returns: True if valid, False otherwise
        """
        return len(self.vertices) >= 3 and self.area() > 0.0
    
    def validate_vertices(self) -> Dict[str, any]:
        """Comprehensive validation of polygon vertices.
        
        Performs detailed checks on the polygon's vertices including:
        - Basic validity (minimum vertices, non-zero area)
        - Geometric properties (self-intersection, degeneracy)
        - Coordinate validity (finite values, reasonable bounds)
        - Winding order consistency
        - Vertex distribution and spacing
        
        Returns:
            Dictionary containing validation results with keys:
            - 'is_valid': bool - Overall validity
            - 'errors': List[str] - List of error messages
            - 'warnings': List[str] - List of warning messages
            - 'properties': Dict - Geometric properties of the polygon
        """
        errors = []
        warnings = []
        properties = {}
        
        # Basic validation
        if not self.vertices:
            errors.append("No vertices defined")
            return {
                'is_valid': False,
                'errors': errors,
                'warnings': warnings,
                'properties': properties
            }
        
        if len(self.vertices) < 3:
            errors.append(f"Insufficient vertices: {len(self.vertices)} "
                         f"(minimum 3 required)")
        
        # Check for finite coordinates
        for i, vertex in enumerate(self.vertices):
            if not isinstance(vertex, (Point)):
                errors.append(f"Vertex {i} is not a valid 2D coordinate: "
                             f"{vertex}")
                continue
            
            x, y = vertex.x, vertex.y
            if not (isinstance(x, (int, float)) and 
                   isinstance(y, (int, float))):
                errors.append(f"Vertex {i} contains non-numeric "
                             f"coordinates: ({x}, {y})")
                continue
            
            if not (math.isfinite(x) and math.isfinite(y)):
                errors.append(f"Vertex {i} contains non-finite "
                             f"coordinates: ({x}, {y})")
                continue
        
        # If we have basic errors, return early
        if errors:
            return {
                'is_valid': False,
                'errors': errors,
                'warnings': warnings,
                'properties': properties
            }
        
        # Calculate geometric properties
        area = self.area()
        signed_area = self.signed_area()
        properties['area'] = area
        properties['signed_area'] = signed_area
        properties['is_clockwise'] = self.is_clockwise()
        properties['vertex_count'] = len(self.vertices)
        
        # Check for zero or negative area
        if area <= 0:
            errors.append(f"Invalid area: {area} (must be positive)")
        
        # Check for very small area that might indicate degenerate polygon
        min_x, min_y, max_x, max_y = self.bounding_box()
        bbox_area = (max_x - min_x) * (max_y - min_y)
        properties['bounding_box_area'] = bbox_area
        properties['area_efficiency'] = area / bbox_area if bbox_area > 0 else 0
        
        if area < 1.0:
            warnings.append(f"Very small polygon area: {area:.2f}")
        
        if bbox_area > 0 and area / bbox_area < 0.1:
            warnings.append(f"Low area efficiency: {area/bbox_area:.2%} "
                           f"(polygon is very sparse)")
        
        # Check for duplicate consecutive vertices
        duplicate_count = 0
        for i in range(len(self.vertices)):
            current = self.vertices[i]
            next_vertex = self.vertices[(i + 1) % len(self.vertices)]
            if current == next_vertex:
                errors.append(f"Duplicate consecutive vertices at positions "
                             f"{i} and {(i+1)%len(self.vertices)}: "
                             f"{current}")
                duplicate_count += 1
        
        properties['duplicate_vertices'] = duplicate_count
        
        # Check for collinear consecutive vertices (three points in a line)
        collinear_count = 0
        for i in range(len(self.vertices)):
            if len(self.vertices) < 3:
                break
            
            p1 = self.vertices[i]
            p2 = self.vertices[(i + 1) % len(self.vertices)]
            p3 = self.vertices[(i + 2) % len(self.vertices)]
            
            # Calculate cross product to check collinearity
            cross_product = ((p2.x - p1.x) * (p3.y - p1.y) - 
                              (p2.y - p1.y) * (p3.x - p1.x))

            if abs(cross_product) < 1e-6:  # Essentially collinear
                warnings.append(f"Collinear vertices found at positions "
                               f"{i}, {(i+1)%len(self.vertices)}, "
                               f"{(i+2)%len(self.vertices)}")
                collinear_count += 1
        
        properties['collinear_vertices'] = collinear_count
        
        # Check for self-intersection
        intersection_count = self._count_self_intersections()
        properties['self_intersections'] = intersection_count
        
        if intersection_count > 0:
            errors.append(f"Self-intersecting polygon: "
                         f"{intersection_count} intersections found")
        
        # Check vertex spacing and distribution
        edge_lengths = []
        for i in range(len(self.vertices)):
            p1 = self.vertices[i]
            p2 = self.vertices[(i + 1) % len(self.vertices)]
            length = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
            edge_lengths.append(length)
        
        if edge_lengths:
            properties['min_edge_length'] = min(edge_lengths)
            properties['max_edge_length'] = max(edge_lengths)
            properties['avg_edge_length'] = (sum(edge_lengths) / 
                                             len(edge_lengths))
            
            # Check for very short edges
            very_short_edges = [i for i, length in enumerate(edge_lengths) 
                               if length < 1.0]
            if very_short_edges:
                warnings.append(f"Very short edges found at positions: "
                               f"{very_short_edges}")
            
            # Check for highly irregular edge distribution
            if len(edge_lengths) > 1:
                edge_variance = sum((length - properties['avg_edge_length'])**2 for length in edge_lengths) / len(edge_lengths)
                properties['edge_length_variance'] = edge_variance
                
                if properties['avg_edge_length'] > 0:
                    coefficient_of_variation = math.sqrt(edge_variance) / properties['avg_edge_length']
                    properties['edge_length_cv'] = coefficient_of_variation
                    
                    if coefficient_of_variation > 2.0:
                        warnings.append(f"Highly irregular edge lengths (CV: {coefficient_of_variation:.2f})")
        
        # Check bounds reasonableness (assuming screen coordinates)
        reasonable_bounds = (-1000, -1000, 10000, 10000)  # Reasonable screen coordinate bounds
        if (min_x < reasonable_bounds[0] or min_y < reasonable_bounds[1] or 
            max_x > reasonable_bounds[2] or max_y > reasonable_bounds[3]):
            warnings.append(f"Vertices outside reasonable bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")
        
        properties['bounding_box'] = (min_x, min_y, max_x, max_y)
        properties['width'] = max_x - min_x
        properties['height'] = max_y - min_y
        
        # Check aspect ratio
        if properties['height'] > 0:
            aspect_ratio = properties['width'] / properties['height']
            properties['aspect_ratio'] = aspect_ratio
            
            if aspect_ratio > 10 or aspect_ratio < 0.1:
                warnings.append(f"Extreme aspect ratio: {aspect_ratio:.2f}")
        
        # Overall validity check
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'properties': properties
        }
    
    def _count_self_intersections(self) -> int:
        """Count the number of self-intersections in the polygon.
        
        Returns:
            Number of self-intersection points found
        """
        if len(self.vertices) < 4:
            return 0  # Need at least 4 vertices to have self-intersection
        
        intersections = 0
        
        # Check each pair of non-adjacent edges
        for i in range(len(self.vertices)):
            for j in range(i + 2, len(self.vertices)):
                # Skip adjacent edges (they share a vertex by definition)
                if j == len(self.vertices) - 1 and i == 0:
                    continue
                
                # Get edge endpoints
                p1 = self.vertices[i]
                p2 = self.vertices[(i + 1) % len(self.vertices)]
                p3 = self.vertices[j]
                p4 = self.vertices[(j + 1) % len(self.vertices)]
                
                # Check if edges intersect (excluding endpoints)
                if self._edges_intersect(p1, p2, p3, p4):
                    intersections += 1
        
        return intersections

    def _edges_intersect(self, 
            p1: Point, p2: Point, 
            p3: Point, p4: Point) -> bool:
        """Check if two line segments intersect (excluding endpoints).
        
        Args:
            p1, p2: First line segment endpoints
            p3, p4: Second line segment endpoints
            
        Returns:
            True if segments intersect (not including shared endpoints)
        """
        def ccw(A, B, C):
            return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
        
        # Check if endpoints are the same (adjacent edges)
        if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
            return False
        
        # Check if line segments intersect
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def create_polygon_to_fill_space(
        dimensions: Tuple[int, int], portion: float = 0.75,
        attempt:int=0
    ) -> PolygonTerritory:
    """Create a realistic polygon using random walk between eclipse control points.
    
    Args:
        dimensions: (width, height) of the available space
        portion: Portion of the total area the polygon should occupy (0.0 to 1.0)
        
    Returns:
        PolygonTerritory with jagged eclipse-like shape
    """
    if attempt > 25:
        raise ValueError("Failed to create a valid polygon after multiple attempts.")

    width, height = dimensions
    
    # Calculate the target area and eclipse dimensions
    target_area = width * height * portion
    
    # Create eclipse parameters to achieve target area
    # Area of eclipse = π * a * b, where a and b are semi-axes
    # We'll use a ratio to make it look natural (not perfectly circular)
    aspect_ratio = random.uniform(0.6, 1.4)  # Eclipse aspect ratio
    
    # Solve for semi-axes: target_area = π * a * b, and b = a * aspect_ratio
    # So: target_area = π * a² * aspect_ratio
    semi_axis_a = math.sqrt(target_area / (math.pi * aspect_ratio))
    semi_axis_b = semi_axis_a * aspect_ratio
    
    # Center the eclipse in the available space
    center_x = width / 2
    center_y = height / 2
    
    # Ensure eclipse fits within bounds with some margin
    margin = 50
    max_radius_x = (width - 2 * margin) / 2
    max_radius_y = (height - 2 * margin) / 2
    
    # Scale down if necessary
    if semi_axis_a > max_radius_x:
        scale_factor = max_radius_x / semi_axis_a
        semi_axis_a *= scale_factor
        semi_axis_b *= scale_factor
    
    if semi_axis_b > max_radius_y:
        scale_factor = max_radius_y / semi_axis_b
        semi_axis_a *= scale_factor
        semi_axis_b *= scale_factor
    
    # Generate control points around the eclipse
    num_control_points = 25  # Number of control points around eclipse
    control_points = []
    
    for i in range(num_control_points):
        angle = (2 * math.pi * i) / num_control_points
        
        # Add some angular variation for more natural shape
        angle_variation = random.uniform(-0.2, 0.2)
        varied_angle = angle + angle_variation
        
        # Calculate base eclipse point
        base_x = center_x + semi_axis_a * math.cos(varied_angle)
        base_y = center_y + semi_axis_b * math.sin(varied_angle)
        
        # Add radial variation to make it more jagged
        radial_variation = random.uniform(0.7, 1.3)
        
        # Apply variation
        final_x = center_x + (base_x - center_x) * radial_variation
        final_y = center_y + (base_y - center_y) * radial_variation
        
        # Ensure point stays within bounds
        final_x = max(margin, min(width - margin, final_x))
        final_y = max(margin, min(height - margin, final_y))
        
        control_points.append((final_x, final_y))
    
    # Now create random walk between consecutive control points
    vertices = []
    
    for i in range(len(control_points)):
        start_point = control_points[i]
        end_point = control_points[(i + 1) % len(control_points)]
        
        # Generate random walk between start and end points
        walk_points = random_walk(
            Point(*start_point), Point(*end_point),
            num_steps=10,
            variation_strength=random.uniform(0.01, 0.15)
        )
        
        # Add walk points (excluding the last point to avoid duplication)
        vertices.extend(walk_points[:-1])
    
    # simplify coordinates
    vertices = [Point(round(p.x, 3), round(p.y, 3)) for p in vertices]

    # Clean up any potential issues
    vertices = clean_sequence(vertices)

    polygon = PolygonTerritory(vertices)
    validation = polygon.validate_vertices()
    if not validation['is_valid']:
        import warnings
        warnings.warn(f"Polygon validation failed on attempt {attempt}: {validation['errors']}", RuntimeWarning)
        return create_polygon_to_fill_space(dimensions, portion, attempt + 1)
    
    return polygon




class BoardGenerator:
    """Generates dynamic Risk-like boards using polygon subdivision."""
    
    def __init__(self, width: int = 1000, height: int = 600):
        """Initialize the board generator.
        
        Args:
            width: Board width for territory placement
            height: Board height for territory placement
        """
        self.width = width
        self.height = height
        self.margin = 50  # Margin from edges
        
    def generate_board(self, game_state: GameState) -> None:
        """Generate territories using polygon subdivision.
        
        Args:
            game_state: GameState to populate with territories
        """
        # Create the initial large continent polygon
        initial_polygon = create_polygon_to_fill_space(
            (self.width, self.height), portion=0.90
        )
        print(f"Created initial continent with {len(initial_polygon.vertices)} vertices, area: {initial_polygon.area():.2f}")
        
        # Subdivide the polygon into the desired number of territories
        territory_polygons = self._subdivide_continent(initial_polygon, game_state.regions)
        
        # Convert polygon territories to actual Territory objects
        territories = []
        for i, poly_territory in enumerate(territory_polygons):
            territory = self._create_territory_from_polygon(i, poly_territory)
            territories.append(territory)
            game_state.add_territory(territory)
        
        # Calculate adjacency relationships
        self._calculate_adjacencies(territories)
        
        # Assign territories to players
        self._assign_initial_territories(game_state, territories)
        
        # Update player statistics
        game_state.update_player_statistics()

    
    def _subdivide_continent(self, initial_polygon: PolygonTerritory, 
                           target_regions: int) -> List[PolygonTerritory]:
        """Subdivide the continent into the target number of regions.
        
        Args:
            initial_polygon: The initial continent polygon
            target_regions: Desired number of territories
            
        Returns:
            List of PolygonTerritory objects representing final territories
        """
        # Start with the initial polygon
        undivided_regions = [initial_polygon]
        
        # Keep dividing until we have enough regions
        while len(undivided_regions) < target_regions:
            region_to_divide = max(undivided_regions, key=lambda r: r.area())
            undivided_regions.remove(region_to_divide)
            try:
                divided_regions = region_to_divide.divide()
                undivided_regions.extend(divided_regions)
            except ValueError:
                # If division fails, re-add the region and try again
                undivided_regions.append(region_to_divide)

        return undivided_regions
        
    def _create_territory_from_polygon(self, territory_id: int, 
                                     poly_territory: PolygonTerritory) -> Territory:
        """Create a Territory object from a PolygonTerritory.
        
        Args:
            territory_id: Unique territory ID
            poly_territory: PolygonTerritory to convert
            
        Returns:
            Territory object
        """
        # Generate territory name
        territory_name = f"Region {territory_id + 1}"
        
        # Assign continent based on position (create multiple continents)
        continent_name = self._assign_continent(poly_territory, territory_id)
        
        territory = Territory(
            id=territory_id,
            name=territory_name,
            center=poly_territory.center,
            vertices=poly_territory.vertices,
            continent=continent_name
        )
        
        return territory
    
    def _assign_continent(self, poly_territory: PolygonTerritory, territory_id: int) -> str:
        """Assign a continent name based on territory position.
        
        Args:
            poly_territory: PolygonTerritory to assign continent to
            territory_id: Territory ID for variation
            
        Returns:
            Continent name
        """
        # Create continent names
        continent_names = [
            "North America", "Europe", "Asia", "Africa", 
            "South America", "Australia", "Antarctica", "Middle East"
        ]
        
        # Assign based on position on screen
        center_x, center_y = poly_territory.center
        
        # Divide screen into regions for continent assignment
        screen_thirds_x = self.width // 3
        screen_thirds_y = self.height // 3
        
        continent_id = 0
        if center_x < screen_thirds_x:
            continent_id = 0 if center_y < screen_thirds_y * 2 else 1
        elif center_x < screen_thirds_x * 2:
            continent_id = 2 if center_y < screen_thirds_y * 2 else 3
        else:
            continent_id = 4 if center_y < screen_thirds_y * 2 else 5
        
        return continent_names[continent_id % len(continent_names)]
    def _calculate_adjacencies(self, territories: List[Territory]) -> None:
        """Calculate which territories are adjacent based on shared boundaries.
        
        Args:
            territories: List of all territories to analyze
        """
        print(f"Calculating adjacencies for {len(territories)} territories...")
        
        for i, territory_a in enumerate(territories):
            for j, territory_b in enumerate(territories):
                if i >= j:  # Skip self and already processed pairs
                    continue
                
                # Check if territories share a boundary
                if self._territories_share_boundary(territory_a, territory_b):
                    territory_a.add_adjacent_territory(territory_b.id)
                    territory_b.add_adjacent_territory(territory_a.id)
        
        # Report adjacency statistics
        total_adjacencies = sum(len(t.adjacent_territories) for t in territories)
        avg_adjacencies = total_adjacencies / len(territories) if territories else 0
        print(f"Adjacency calculation complete: {total_adjacencies} total connections, "
              f"{avg_adjacencies:.1f} average per territory")
    
    def _territories_share_boundary(self, territory_a: Territory, territory_b: Territory) -> bool:
        """Check if two territories share a boundary (have adjacent edges).
        
        Args:
            territory_a: First territory
            territory_b: Second territory
            
        Returns:
            True if territories share a boundary edge
        """
        vertices_a = territory_a.vertices
        vertices_b = territory_b.vertices
        
        # Check if any edge from territory A is shared with territory B
        for i in range(len(vertices_a)):
            edge_start = vertices_a[i]
            edge_end = vertices_a[(i + 1) % len(vertices_a)]
            
            # Check if this edge exists in territory B (in either direction)
            if self._edge_exists_in_polygon(edge_start, edge_end, vertices_b):
                return True
        
        return False
    
    def _edge_exists_in_polygon(self, start: Tuple[int, int], end: Tuple[int, int], 
                               vertices: List[Tuple[int, int]]) -> bool:
        """Check if an edge exists in a polygon (in either direction).
        
        Args:
            start: Start point of the edge
            end: End point of the edge
            vertices: Polygon vertices to search
            
        Returns:
            True if the edge exists in the polygon
        """
        for i in range(len(vertices)):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % len(vertices)]
            
            # Check both directions of the edge
            if ((v1 == start and v2 == end) or 
                (v1 == end and v2 == start)):
                return True
        
        return False
    
    def _create_territory_from_polygon(self, territory_id: int, 
                                     poly_territory: PolygonTerritory) -> Territory:
        """Create a Territory object from a PolygonTerritory.
        
        Args:
            territory_id: Unique ID for the territory
            poly_territory: PolygonTerritory to convert
            
        Returns:
            Territory object with proper initialization
        """
        # Calculate center point
        center_x = sum(p.x for p in poly_territory.vertices) // len(poly_territory.vertices)
        center_y = sum(p.y for p in poly_territory.vertices) // len(poly_territory.vertices)

        # Create the territory
        territory = Territory(
            id=territory_id,
            name=f"Territory {territory_id + 1}",
            center=(center_x, center_y),
            vertices=[ v.to_tuple() for v in poly_territory.vertices ],
            continent="Continent A"
        )
        
        return territory
    
    def _assign_initial_territories(self, game_state: 'GameState', territories: List[Territory]) -> None:
        """Assign territories to players and give them initial armies.
        
        Args:
            game_state: GameState containing players
            territories: List of territories to assign
        """
        # Shuffle territories for random assignment
        shuffled_territories = territories.copy()
        random.shuffle(shuffled_territories)
        
        # Assign territories to players in round-robin fashion
        players = list(game_state.players.values())
        for i, territory in enumerate(shuffled_territories):
            player = players[i % len(players)]
            
            # Start with 1 army per territory, then distribute remaining armies
            initial_armies = 1
            territory.set_owner(player.id, initial_armies)
        
        # Calculate how many armies each player should get (s armies per player)
        armies_per_player = game_state.starting_armies
        
        # Calculate how many armies each player already has from territory assignment
        player_armies = {player.id: 0 for player in players}
        for territory in territories:
            if territory.owner is not None:
                player_armies[territory.owner] += territory.armies
        
        # Distribute remaining armies to each player individually
        for player in players:
            armies_already_placed = player_armies[player.id]
            remaining_armies_for_player = armies_per_player - armies_already_placed
            
            # Get territories owned by this player
            player_territories = [t for t in territories if t.owner == player.id]
            
            # Distribute remaining armies randomly among this player's territories
            for _ in range(remaining_armies_for_player):
                if player_territories:  # Safety check
                    territory = random.choice(player_territories)
                    territory.armies += 1
        
        # Verify army distribution is correct
        print("Initial army distribution verification:")
        for player in players:
            player_territories = [t for t in territories if t.owner == player.id]
            total_armies = sum(t.armies for t in player_territories)
            print(f"Player {player.id} ({player.name}): {len(player_territories)} territories, {total_armies} armies (expected: {armies_per_player})")
            
            if total_armies != armies_per_player:
                print(f"ERROR: Player {player.id} has {total_armies} armies but should have {armies_per_player}")


def generate_sample_board(game_state: GameState, width: int = 1000, height: int = 600) -> None:
    """Convenience function to generate a board for a game state using polygon subdivision. Creates territories and assigns them to players.
    
    :param game_state: GameState to populate with generated territories and assignments
    :param width: Board width in pixels for territory generation
    :param height: Board height in pixels for territory generation
    """
    generator = BoardGenerator(width, height)
    generator.generate_board(game_state)