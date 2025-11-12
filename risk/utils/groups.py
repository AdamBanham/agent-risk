from risk.state import Territory
from risk.utils.logging import info
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

        # Start a new group
        group: List[Territory] = []
        queue: deque[int] = deque()
        queue.append(territory.id)
        visited.add(territory.id)

        # Perform BFS to find all connected territories with the same owner
        info(f"Starting new group from territory {territory.id} owned by player {territory.owner}")
        while queue:
            current_id = queue.pop()
            current_territory = territory_map[current_id]
            group.append(current_territory)

            for neighbor in current_territory.adjacent_territories:
                if (
                    neighbor.id in territory_map
                    and neighbor.id not in visited
                    and neighbor.owner == current_territory.owner
                ):
                    visited.add(neighbor.id)
                    queue.append(neighbor.id)
        info("group size: {}".format(len(group)))
        groups.append(group)
    return groups
