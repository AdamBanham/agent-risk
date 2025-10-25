"""
Core game state classes for the Risk simulation.
Manages players, game state, and overall simulation state.
"""

from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import time

from .territory import Territory
from .ui import TurnUI
from .turn_manager import TurnManager


@dataclass
class UIState:
    selected_territory_id: Optional[int] = None


class GamePhase(Enum):
    """Possible phases of the game."""

    INIT = "init"  # Initial setup
    GAME_TURN = "game_turn"  # Main game loop
    PLAYER_TURN = "player_turn"  # Individual player actions
    GET_TROOPS = "get_troops"  # Reinforcement distribution
    PLACE_TROOPS = "place_troops"  # Troop placement phase
    MOVE_TROOPS = "move_troops"  # Attack/movement phase
    END_TURN = "end_turn"  # Turn cleanup
    GAME_END = "game_end"  # Game finished
    SCORE = "score"  # Post-game scoring

    def __repr__(self):
        return f"GamePhase.{self.name}"


@dataclass
class Player:
    """Represents a player in the game."""

    id: int
    name: str
    color: Tuple[int, int, int]  # RGB color for rendering
    is_active: bool = True
    is_human: bool = False  # False for AI agents

    # Game statistics
    territories_controlled: Set[int] = field(default_factory=set)
    total_armies: int = 0
    reinforcements_available: int = 0

    def get_territory_count(self) -> int:
        """
        Get the number of territories controlled by this player. Returns the
        size of the controlled territories set.

        :returns: Number of territories controlled by this player
        """
        return len(self.territories_controlled)

    def is_eliminated(self) -> bool:
        """
        Check if this player has been eliminated. A player is eliminated
        when they control no territories.

        :returns: True if player controls no territories and is eliminated,
                 False otherwise
        """
        return len(self.territories_controlled) == 0

    def __repr__(self) -> str:
        """String representation for debugging."""
        ret = "Player("
        for attr, value in self.__dict__.items():
            ret += f"\n\t{attr}={repr(value)},"
        return ret + ")"


@dataclass
class GameState:
    """Represents the complete state of a Risk game simulation.

    This is the main game state class that contains all information
    about territories, players, and game progression.
    """

    # Game configuration
    regions: int  # Number of territories (g parameter)
    num_players: int  # Number of players (p parameter)
    starting_armies: int  # Starting army size (s parameter)

    # Game state
    phase: GamePhase = GamePhase.INIT
    current_turn: int = 0
    total_turns: int = 0  # Total number of turns completed in simulation
    current_player_id: Optional[int] = 0
    winner_id: Optional[int] = None
    starting_player: int = 0
    placements_left: int = 0

    # Game entities
    territories: Dict[int, Territory] = field(default_factory=dict)
    players: Dict[int, Player] = field(default_factory=dict)

    # Timing and metadata
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # rendering
    screen_width: int = 1800
    screen_height: int = 1028

    # UI state
    ui_state: UIState = field(default_factory=UIState)
    ui_turn_manager: TurnManager = field(default_factory=lambda: None)
    ui_turn_state: TurnUI = field(default_factory=lambda: None)

    @classmethod
    def create_new_game(
        cls, regions: int, num_players: int, starting_armies: int
    ) -> "GameState":
        """
        Create a new game state with the specified parameters. Factory
        method for consistent initialization.

        :param regions: Number of territories to generate (g parameter)
        :param num_players: Number of players in the game (p parameter)
        :param starting_armies: Starting army size per player (s parameter)
        :returns: New GameState instance with initialized players and
                 default colors
        """
        game_state = cls(
            regions=regions, num_players=num_players, starting_armies=starting_armies
        )

        # Initialize players
        player_colors = [
            (200, 50, 50),  # Red
            (50, 200, 50),  # Green
            (50, 50, 200),  # Blue
            (200, 200, 50),  # Yellow
            (200, 50, 200),  # Magenta
            (50, 200, 200),  # Cyan
            (150, 75, 0),  # Brown
            (255, 165, 0),  # Orange
        ]

        for i in range(num_players):
            player = Player(
                id=i,
                name=f"Player {i + 1}",
                color=player_colors[i % len(player_colors)],
            )
            game_state.players[i] = player

        return game_state

    def set_adjacent_territories(self) -> None:
        """
        Determine and set adjacent territories based on shared vertices.
        Updates each territory's adjacency list.
        """
        for territory in self.territories.values():
            for other in self.territories.values():
                if other.id == territory.id:
                    continue
                shared_vertices = any(
                    vertex in other.vertices for vertex in territory.vertices
                )
                if shared_vertices:
                    territory.add_adjacent_territory(other)
                    other.add_adjacent_territory(territory)

    def initialise(self, generate_board: bool = True) -> None:
        """
        Set up initial game state.
        """
        # set territories
        if not self.territories or generate_board:
            from ..state.board_generator import generate_sample_board

            generate_sample_board(self, self.screen_width, self.screen_height - 120)
            print(f"Generated initial board with {len(self.territories)} territories")
        else:
            # determine adjacencies
            self.set_adjacent_territories()

        # set first player
        self.current_player_id = random.choice(list(self.players.keys()))
        self.starting_player = self.current_player_id

        self.ui_turn_manager = TurnManager(self)
        self.ui_turn_state = TurnUI(self.screen_width, self.screen_height)

        self.phase = GamePhase.PLAYER_TURN

    def calculate_reinforcements(self, player_id: int) -> int:
        """
        Work out the reinforcements for the given player.

        :param player_id:
            the player to consider for reinforcements

        :returns:
            the number of reinforcements
        """
        territory_count = self.get_player(player_id).get_territory_count()
        return max(3, territory_count // 3)

    def add_territory(self, territory: Territory) -> None:
        """
        Add a territory to the game state. Updates the territories
        dictionary and timestamps.

        :param territory: Territory object to add to the game state
        """
        self.territories[territory.id] = territory
        self.last_updated = time.time()

    def get_territory(self, territory_id: int) -> Optional[Territory]:
        """
        Get a territory by ID. Returns the territory from the game state
        dictionary.

        :param territory_id: ID of the territory to retrieve
        :returns: Territory if found, None otherwise
        """
        return self.territories.get(territory_id)

    def get_player(self, player_id: int) -> Optional[Player]:
        """
        Get a player by ID. Returns the player from the game state
        dictionary.

        :param player_id: ID of the player to retrieve
        :returns: Player if found, None otherwise
        """
        return self.players.get(player_id)

    def get_active_players(self) -> List[Player]:
        """
        Get all active (non-eliminated) players. Filters players based on
        is_active flag and elimination status.

        :returns: List of active players who are still in the game
        """
        return [
            player
            for player in self.players.values()
            if player.is_active and not player.is_eliminated()
        ]

    def get_territories_owned_by(self, player_id: int) -> List[Territory]:
        """
        Get all territories owned by a specific player. Filters territories
        by owner ID.

        :param player_id: ID of the player whose territories to retrieve
        :returns: List of territories owned by the specified player
        """
        return [
            territory
            for territory in self.territories.values()
            if territory.is_owned_by(player_id)
        ]

    def get_free_territories(self) -> List[Territory]:
        """
        Get all unowned territories. Filters territories that are currently
        free (no owner).

        :returns: List of free territories that have no current owner
        """
        return [
            territory for territory in self.territories.values() if territory.is_free()
        ]

    def advance_turn(self) -> None:
        """
        Advance to the next player's turn. Cycles through active players
        and increments turn counter.
        """
        # Get all players who are still active (not eliminated)
        active_players = [p for p in self.players.values() if p.is_active]

        if len(active_players) <= 1:
            return

        next_id = (self.current_player_id + 1) % len(self.players.keys())
        self.current_player_id = next_id
        
        if self.current_player_id == self.starting_player:
            self.total_turns += 1
            self.current_turn += 1
        
        next_player = self.get_player(self.current_player_id)
        if not next_player.is_active:
            return self.advance_turn()

        self.last_updated = time.time()
        return 

    def check_victory_condition(self) -> Optional[int]:
        """
        Check if any player has won the game. Checks for single remaining
        player or total territory control.

        :returns: ID of winning player, or None if no winner yet
        """
        active_players = self.get_active_players()

        if len(active_players) == 1:
            self.winner_id = active_players[0].id
            self.phase = GamePhase.GAME_END
            return self.winner_id

        # Check if any player controls all territories
        for player in active_players:
            if player.get_territory_count() == len(self.territories):
                self.winner_id = player.id
                self.phase = GamePhase.GAME_END
                return player.id

        return None

    def update_player_statistics(self) -> None:
        """
        Update all player statistics based on current territory ownership.
        Recalculates territory counts and armies for all players.
        """
        # Reset all player territory sets
        for player in self.players.values():
            terrs = self.get_territories_owned_by(player.id)
            player.territories_controlled = set(
                [
                    t.id
                    for t 
                    in terrs
                ]
            )

            player.total_armies = sum(
                t.armies
                for t 
                in terrs
            )

        # Check for eliminated players
        for player in self.players.values():
            if player.is_eliminated() and player.is_active:
                player.is_active = False

        self.last_updated = time.time()

    def get_game_summary(self) -> Dict:
        """
        Get a summary of the current game state. Provides key information
        about the game's current status.

        :returns: Dictionary with game state summary including phase, turns,
                 players, and territories
        """
        return {
            "phase": self.phase.value,
            "turn": self.current_turn,
            "total_turns": self.total_turns,
            "current_player": self.current_player_id,
            "winner": self.winner_id,
            "active_players": len(self.get_active_players()),
            "total_territories": len(self.territories),
            "free_territories": len(self.get_free_territories()),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        ret = "GameState("

        non_inserted = [
            "ui_state",
            "ui_turn_manager",
            "ui_turn_state"
        ]

        for attr, value in self.__dict__.items():
            if attr in non_inserted:
                continue
            ret += f"\n\t{attr}={repr(value)},"

        return ret + ")"
