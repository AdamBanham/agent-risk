"""
Territory data structures for the Risk simulation.
Defines Territory class with ownership states and adjacency tracking.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from enum import Enum


class TerritoryState(Enum):
    """
    Possible states for a territory.

    .. attributes::
        FREE
            No owner, available for occupation
        OWNED
            Controlled by a single player
        CONTESTED
            disputed ownership between many players
    """

    FREE = "free"
    OWNED = "owned"
    CONTESTED = "contested"

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


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
    state: TerritoryState = field(default_factory=lambda: TerritoryState.FREE)
    owner: Optional[int] = None  # Player ID (None if FREE)
    armies: int = 0
    selected: bool = False  # Whether this territory is currently selected

    # Adjacency and connectivity
    adjacent_territories: Set["Territory"] = field(default_factory=set)

    def __post_init__(self):
        """Validate territory state consistency after initialization."""
        # Ensure state consistency
        if self.owner is not None and self.state == TerritoryState.FREE:
            self.state = TerritoryState.OWNED
        elif self.owner is None and self.state in (
            TerritoryState.OWNED,
            TerritoryState.CONTESTED,
        ):
            self.state = TerritoryState.FREE

    def add_adjacent_territory(self, territory: "Territory") -> None:
        """
        Add a territory as adjacent to this one. Updates the adjacency set
        for pathfinding and movement rules.

        :param territory_id: ID of the adjacent territory to add
        """
        self.adjacent_territories.add(territory)

    def remove_adjacent_territory(self, territory: "Territory") -> None:
        """
        Remove a territory from adjacency list. Updates the adjacency set
        when territories are no longer connected.

        :param territory_id: ID of the territory to remove from adjacency
        """
        self.adjacent_territories.discard(territory)

    def is_adjacent_to(self, territory_id: int) -> bool:
        """
        Check if this territory is adjacent to another. Used for movement
        and attack validation.

        :param territory_id: ID of the territory to check adjacency with
        :returns: True if territories are adjacent, False otherwise
        """
        return territory_id in [t.id for t in self.adjacent_territories]

    def set_owner(self, player_id: Optional[int], army_count: int = 0) -> None:
        """
        Set the owner of this territory. Updates ownership and army count,
        handles state transitions.

        :param player_id: ID of the owning player (None for free territory)
        :param army_count: Number of armies to place on the territory
        """
        self.owner = player_id
        self.armies = army_count

        if player_id is None:
            self.state = TerritoryState.FREE
            self.armies = 0
        else:
            self.state = TerritoryState.OWNED

    def set_contested(self) -> None:
        """
        Mark this territory as contested (under attack). Changes state to
        contested if territory has an owner.
        """
        if self.owner is not None:
            self.state = TerritoryState.CONTESTED

    def resolve_contest(self, winner_id: Optional[int], army_count: int = 0) -> None:
        """
        Resolve a contest for this territory. Sets new owner and army count
        after battle resolution.

        :param winner_id: ID of the winning player (None if territory
                         becomes free)
        :param army_count: Number of armies for the winner after the contest
        """
        self.set_owner(winner_id, army_count)

    def add_armies(self, count: int) -> None:
        """
        Add armies to this territory. Increases the army count by the
        specified amount.

        :param count: Number of armies to add (must be positive)
        """
        if count > 0:
            self.armies += count

    def remove_armies(self, count: int) -> int:
        """
        Remove armies from this territory. Decreases army count up to the
        available amount.

        :param count: Number of armies to remove
        :returns: Actual number of armies removed (limited by available
                 armies)
        """
        if count <= 0:
            return 0

        removed = min(count, self.armies)
        self.armies -= removed
        return removed

    def can_attack_from(self) -> bool:
        """
        Check if this territory can launch attacks. Requires ownership and
        more than 1 army to attack.

        :returns: True if territory has owner and more than 1 army, False
                 otherwise
        """
        return (
            self.owner is not None
            and self.state == TerritoryState.OWNED
            and self.armies > 1
        )

    def can_be_attacked(self) -> bool:
        """
        Check if this territory can be attacked. Any territory with an owner
        can be contested.

        :returns: True if territory has an owner and can be contested, False
                 otherwise
        """
        return self.owner is not None

    def is_free(self) -> bool:
        """
        Check if territory is free (unowned). Free territories have no owner
        and can be claimed.

        :returns: True if territory has no owner, False otherwise
        """
        return self.state == TerritoryState.FREE

    def is_owned_by(self, player_id: int) -> bool:
        """
        Check if territory is owned by a specific player. Checks ownership
        regardless of contested state.

        :param player_id: Player ID to check ownership against
        :returns: True if territory is owned by the specified player, False
                 otherwise
        """
        return self.owner == player_id and self.state in (
            TerritoryState.OWNED,
            TerritoryState.CONTESTED,
        )

    def set_selected(self, selected: bool = True) -> None:
        """
        Set the selection state of this territory. Used for UI highlighting
        and player interaction.

        :param selected: True to select, False to deselect the territory
        """
        self.selected = selected

    def toggle_selected(self) -> bool:
        """Toggle the selection state of this territory. Switches between selected and deselected states.

        :returns: New selection state after toggling
        """
        self.selected = not self.selected
        return self.selected

    def __repr__(self) -> str:
        """String representation for debugging."""
        ret = "Territory("
        for key in vars(self):
            if key == "vertices":
                ret += f"\n{key}=[\n"
                last = 0
                for next in range(1, len(self.vertices) + 6, 5):
                    ret += "\t"
                    for v in self.vertices[last:next]:
                        ret += f"{repr(v)}, "
                    ret += "\n"
                    last = next
                ret += "], \n"
            elif key == "adjacent_territories":
                ret += f"{key}={repr(set())}, "
            else:
                ret += f"{key}={repr(getattr(self, key))}, "
        return ret + ")"

    def __hash__(self):
        return hash(self.id)
