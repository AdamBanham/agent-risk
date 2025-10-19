
from ..state import Territory

from typing import Union, List, Set, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class Movement:
    src: Territory
    tgt: Territory
    amount: int


def find_movement_sequence(
        src: Territory, 
        tgt: Territory, 
        amount: int) -> Union[None, List[Movement]]:
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
        return None
    
    # Check if source and target have the same owner
    if src.owner != tgt.owner or src.owner is None:
        return None
    
    # Check if source has enough armies (must leave at least 1)
    if src.armies <= amount:
        return None
    
    # If source and target are the same, no movement needed
    if src.id == tgt.id:
        return []
    
    # If source and target are adjacent, direct movement
    if tgt in src.adjacent_territories:
        return [Movement(src=src, tgt=tgt, amount=amount)]
    
    # Use BFS to find shortest path through owned territories
    path = _find_path_bfs(src, tgt)
    if not path:
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
        movements.append(Movement(
            src=path[i],
            tgt=path[i + 1],
            amount=amount
        ))
    
    return movements