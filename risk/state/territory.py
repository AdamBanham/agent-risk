"""
Territory data structures for the Risk simulation.
Defines Territory class with ownership states and adjacency tracking.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from enum import Enum

from pygame.draw import polygon

class TerritoryState(Enum):
    """Possible states for a territory."""
    FREE = "free"           # No owner, available for occupation
    OWNED = "owned"         # Controlled by a single player
    CONTESTED = "contested" # Under attack or disputed ownership


@dataclass
class Territory:
    """Represents a territory on the board with game state information.
    
    This class contains both the visual representation (polygon) and 
    the game state (ownership, armies, adjacency) of a territory.
    """
    id: int
    name: str
    center: Tuple[int, int]  # (x, y) center position for rendering
    vertices: List[Tuple[int, int]]  # Polygon vertices for rendering
    continent: str = "Unknown"
    
    # Game state properties
    state: TerritoryState = TerritoryState.FREE
    owner: Optional[int] = None  # Player ID (None if FREE)
    armies: int = 0
    selected: bool = False  # Whether this territory is currently selected
    
    # Adjacency and connectivity
    adjacent_territories: Set[int] = field(default_factory=set)  # Territory IDs
    
    def __post_init__(self):
        """Validate territory state consistency after initialization."""
        # Ensure state consistency
        if self.owner is not None and self.state == TerritoryState.FREE:
            self.state = TerritoryState.OWNED
        elif self.owner is None and self.state in (TerritoryState.OWNED, TerritoryState.CONTESTED):
            self.state = TerritoryState.FREE
    
    def add_adjacent_territory(self, territory_id: int) -> None:
        """Add a territory as adjacent to this one.
        
        Args:
            territory_id: ID of the adjacent territory
        """
        self.adjacent_territories.add(territory_id)
    
    def remove_adjacent_territory(self, territory_id: int) -> None:
        """Remove a territory from adjacency list.
        
        Args:
            territory_id: ID of the territory to remove
        """
        self.adjacent_territories.discard(territory_id)
    
    def is_adjacent_to(self, territory_id: int) -> bool:
        """Check if this territory is adjacent to another.
        
        Args:
            territory_id: ID of the territory to check
            
        Returns:
            True if territories are adjacent
        """
        return territory_id in self.adjacent_territories
    
    def set_owner(self, player_id: Optional[int], army_count: int = 0) -> None:
        """Set the owner of this territory.
        
        Args:
            player_id: ID of the owning player (None for free territory)
            army_count: Number of armies to place (default 0)
        """
        self.owner = player_id
        self.armies = army_count
        
        if player_id is None:
            self.state = TerritoryState.FREE
            self.armies = 0
        else:
            self.state = TerritoryState.OWNED
    
    def set_contested(self) -> None:
        """Mark this territory as contested (under attack)."""
        if self.owner is not None:
            self.state = TerritoryState.CONTESTED
    
    def resolve_contest(self, winner_id: Optional[int], army_count: int = 0) -> None:
        """Resolve a contest for this territory.
        
        Args:
            winner_id: ID of the winning player (None if territory becomes free)
            army_count: Number of armies for the winner
        """
        self.set_owner(winner_id, army_count)
    
    def add_armies(self, count: int) -> None:
        """Add armies to this territory.
        
        Args:
            count: Number of armies to add
        """
        if count > 0:
            self.armies += count
    
    def remove_armies(self, count: int) -> int:
        """Remove armies from this territory.
        
        Args:
            count: Number of armies to remove
            
        Returns:
            Actual number of armies removed
        """
        if count <= 0:
            return 0
        
        removed = min(count, self.armies)
        self.armies -= removed
        return removed
    
    def can_attack_from(self) -> bool:
        """Check if this territory can launch attacks.
        
        Returns:
            True if territory has owner and more than 1 army
        """
        return (self.owner is not None and 
                self.state == TerritoryState.OWNED and 
                self.armies > 1)
    
    def can_be_attacked(self) -> bool:
        """Check if this territory can be attacked.
        
        Returns:
            True if territory has an owner (can be contested)
        """
        return self.owner is not None
    
    def is_free(self) -> bool:
        """Check if territory is free (unowned).
        
        Returns:
            True if territory has no owner
        """
        return self.state == TerritoryState.FREE
    
    def is_owned_by(self, player_id: int) -> bool:
        """Check if territory is owned by a specific player.
        
        Args:
            player_id: Player ID to check
            
        Returns:
            True if territory is owned by the specified player
        """
        return (self.owner == player_id and 
                self.state in (TerritoryState.OWNED, TerritoryState.CONTESTED))
    
    def set_selected(self, selected: bool = True) -> None:
        """Set the selection state of this territory.
        
        Args:
            selected: True to select, False to deselect
        """
        self.selected = selected
    
    def toggle_selected(self) -> bool:
        """Toggle the selection state of this territory.
        
        Returns:
            New selection state
        """
        self.selected = not self.selected
        return self.selected
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Territory(id={self.id}, name='{self.name}', "
                f"state={self.state.value}, owner={self.owner}, "
                f"armies={self.armies}, adjacent={len(self.adjacent_territories)})")