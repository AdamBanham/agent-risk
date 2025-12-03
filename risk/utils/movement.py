from risk.state.game_state import GameState
from risk.utils.logging import debug
from ..state import Territory

from typing import Tuple, Union, List, Set, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class Movement:
    src: Territory
    tgt: Territory
    amount: int


def find_movement_sequence(
    src: Territory, tgt: Territory, amount: int
) -> Union[None, List[Movement]]:
    """
    Using BFS find a sequence (if possible) to move troops from src to tgt
    via a sequence of moves between adjacent territories owned by the same player.

    :param src: Source territory to move armies from
    :param tgt: Target territory to move armies to
    :param amount: Number of armies to move
    :returns: List of Movement objects representing the sequence, or None if
             no valid path exists
    """
    # Validate inputs
    if not src or not tgt or amount <= 0:
        raise ValueError(f"Invalid parameters for find_movement_sequence :: {src=}, {tgt=}, {amount=}")
        return None

    # Check if source and target have the same owner
    if src.owner != tgt.owner or src.owner is None:
        raise ValueError("Source and target territories have different owners")
        return None

    # # Check if source has enough armies (must leave at least 1)
    # if src.armies <= amount:
    #     debug("Source territory does not have enough armies to move")
    #     return None

    # If source and target are the same, no movement needed
    if src.id == tgt.id:
        debug("utils::find_movement_sequence::Source and target territories are the same")
        return []

    # If source and target are adjacent, direct movement
    if tgt in src.adjacent_territories:
        return [Movement(src=src, tgt=tgt, amount=amount)]

    # Use BFS to find shortest path through owned territories
    path = _find_path_bfs(src, tgt)
    if not path:
        raise ValueError(f"No valid path found between source {src.id} and target {tgt.id} territories")
        return None

    # Convert path to movement sequence
    return _path_to_movements(path, amount)


def _find_path_bfs(src: Territory, tgt: Territory) -> Optional[List[Territory]]:
    """
    Find shortest path from src to tgt using BFS through territories
    owned by the same player.

    :param src: Source territory
    :param tgt: Target territory
    :returns: List of territories representing the path, or None if no path
    """
    if src.owner != tgt.owner:
        return None

    owner = src.owner
    visited: Set[int] = set()
    queue: deque = deque([(src, [src])])

    while queue:
        current, path = queue.popleft()

        if current.id in visited:
            continue

        visited.add(current.id)

        # Check if we reached the target
        if current.id == tgt.id:
            return path

        # Explore adjacent territories owned by the same player
        for adjacent_territory in current.adjacent_territories:
            if adjacent_territory.id in visited:
                continue

            if adjacent_territory.owner == owner:
                new_path = path + [adjacent_territory]
                queue.append((adjacent_territory, new_path))

    return None


def _path_to_movements(path: List[Territory], amount: int) -> List[Movement]:
    """
    Convert a path of territories into a sequence of movement operations.

    :param path: List of territories representing the movement path
    :param amount: Number of armies to move
    :returns: List of Movement objects representing the sequence
    """
    if len(path) < 2:
        return []

    movements = []
    for i in range(len(path) - 1):
        movements.append(Movement(src=path[i], tgt=path[i + 1], amount=amount))

    return movements


def find_safe_frontline_territories(
    game_state: GameState, player_id: int
) -> Tuple[List[Territory], List[Territory]]:
    """
    Identify safe territories (no adjacent enemies) and front-line territories
    (adjacent to at least one enemy) from a list of owned territories.

    :param owned_territories: List of territories owned by the player
    :param game_state: Current game state for territory lookup
    :returns: Tuple of (safe territories, front-line territories)
    """
    # Get all territories owned by this agent
    owned_territories = game_state.get_territories_owned_by(player_id)

    if len(owned_territories) <= 1:
        return [], []

    # Find territories with and without adjacent enemies
    safe_territories = [
        ter
        for ter in owned_territories
        if all(adj_ter.owner == player_id for adj_ter in ter.adjacent_territories)
    ]
    front_line_territories = [
        ter for ter in owned_territories if ter not in safe_territories
    ]

    return safe_territories, front_line_territories


def find_connected_frontline_territories(
    source_territory: Territory,
    front_line_territories: List[Territory],
    owned_territories: List[Territory],
) -> List[Territory]:
    """
    Find front-line territories reachable from source territory through
    owned territory connections using breadth-first search.

    :param source_territory: Starting territory for pathfinding
    :param front_line_territories: List of target front-line territories
    :param owned_territories: List of all owned territories for pathfinding
    :param game_state: Game state for territory lookup
    :returns: List of reachable front-line territories
    """
    # Create sets for faster lookup
    territories = {t.id: t for t in owned_territories}
    owned_territory_ids = {t.id for t in owned_territories}
    front_line_ids = {t.id for t in front_line_territories}

    # Breadth-first search to find connected territories
    visited = set()
    queue = [source_territory.id]
    visited.add(source_territory.id)
    reachable_frontline = []

    while queue:
        current_id = queue.pop(0)
        current_territory = territories.get(current_id)

        if not current_territory:
            continue

        # Check if this is a front-line territory
        if current_id in front_line_ids:
            # Find the actual territory object
            reachable_frontline.append(territories.get(current_id))

        # Add adjacent owned territories to search queue
        for adjacent in current_territory.adjacent_territories:
            adjacent_id = adjacent.id
            if adjacent_id in owned_territory_ids and adjacent_id not in visited:
                visited.add(adjacent_id)
                queue.append(adjacent_id)

    return reachable_frontline
