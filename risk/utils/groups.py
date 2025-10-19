
from risk.state import Territory
from typing import List, Set, Dict, Optional
from collections import deque


def find_connected_groups(territories: List[Territory]) -> List[List[Territory]]:
    """
    Find all connected groups of territories with the same owner using 
    breadth-first search. Territories are connected if they are adjacent 
    and owned by the same player.
    
    :param territories: List of Territory objects to analyze
    :returns: List of territory groups, where each group is a list of 
             connected territories with the same owner
    """
    if not territories:
        return []
    
    # Create lookup maps for efficient access
    territory_map: Dict[int, Territory] = {t.id: t for t in territories}
    visited: Set[int] = set()
    groups: List[List[Territory]] = []
    
    # Process each unvisited territory
    for territory in territories:
        if territory.id in visited:
            continue
            
        # Start a new connected group with BFS
        group = _find_connected_group_bfs(territory, territory_map, visited)
        if group:
            groups.append(group)
    
    return groups


def _find_connected_group_bfs(start_territory: Territory, 
                             territory_map: Dict[int, Territory],
                             visited: Set[int]) -> List[Territory]:
    """
    Find all territories connected to start_territory with the same owner 
    using breadth-first search.
    
    :param start_territory: Territory to start search from
    :param territory_map: Map of territory ID to Territory object
    :param visited: Set of already visited territory IDs (modified in-place)
    :returns: List of connected territories with same owner as start_territory
    """
    if start_territory.id in visited:
        return []
    
    group: List[Territory] = []
    queue: deque = deque([start_territory])
    target_owner = start_territory.owner
    
    while queue:
        current = queue.popleft()
        
        if current.id in visited:
            continue
            
        # Mark as visited and add to group
        visited.add(current.id)
        group.append(current)
        
        # Check all adjacent territories
        for adjacent_id in current.adjacent_territories:
            if adjacent_id in visited:
                continue
                
            adjacent_territory = territory_map.get(adjacent_id)
            if (adjacent_territory and 
                adjacent_territory.owner == target_owner):
                queue.append(adjacent_territory)
    
    return group


