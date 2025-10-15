"""
Turn management for Risk simulation.
Manages turn phases, placement, attacking, and movement phases.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from .game_state import GameState, Player
from .territory import Territory
from .fight import Fight, FightResult


class TurnPhase(Enum):
    """Specific phases within a player's turn."""
    PLACEMENT = "placement"     # Place reinforcement troops
    ATTACKING = "attacking"     # Attack adjacent territories 
    MOVING = "moving"          # Move troops between owned territories


@dataclass
class AttackState:
    """Represents the state of an ongoing attack."""
    attacker_territory_id: int
    defender_territory_id: int
    max_attacking_armies: int  # Available armies for attack (territory armies - 1)
    defending_armies: int      # Current defending armies
    attacking_armies: int = 1  # Selected attacking army count
    
    def can_attack(self) -> bool:
        """
        Check if attack is valid. Attacker needs at least 2 armies total 
        (1 to stay, 1+ to attack).
        
        :returns: True if attack can proceed, False otherwise
        """
        return (self.attacking_armies >= 1 and 
                self.attacking_armies <= self.max_attacking_armies and
                self.defending_armies >= 1)


@dataclass
class MovementState:
    """Represents the state of an ongoing troop movement."""
    source_territory_id: int
    target_territory_id: int
    max_moving_armies: int     # Available armies for movement (territory armies - 1)
    moving_armies: int = 1     # Selected moving army count
    
    def can_move(self) -> bool:
        """
        Check if movement is valid. Source needs at least 2 armies total 
        (1 to stay, 1+ to move).
        
        :returns: True if movement can proceed, False otherwise
        """
        return (self.moving_armies >= 1 and 
                self.moving_armies <= self.max_moving_armies)


@dataclass
class TurnState:
    """Manages the current state of a player's turn."""
    player_id: int
    phase: TurnPhase = TurnPhase.PLACEMENT
    reinforcements_remaining: int = 0
    placements_made: List[Tuple[int, int]] = field(default_factory=list)  # (territory_id, armies)
    attacks_made: int = 0
    movements_made: int = 0
    
    # Current action states
    current_attack: Optional[AttackState] = None
    current_movement: Optional[MovementState] = None
    current_fight: Optional[Fight] = None
    
    def can_place_reinforcement(self, territory_id: int, armies: int = 1) -> bool:
        """
        Check if reinforcement can be placed. Player must own territory and 
        have reinforcements available.
        
        :param territory_id: ID of territory to place reinforcements in
        :param armies: Number of armies to place (default 1)
        :returns: True if placement is valid, False otherwise
        """
        return (self.phase == TurnPhase.PLACEMENT and 
                self.reinforcements_remaining >= armies and
                armies > 0)
    
    def place_reinforcement(self, territory_id: int, armies: int = 1) -> bool:
        """
        Place reinforcement armies. Updates remaining reinforcements and 
        tracks placement history.
        
        :param territory_id: ID of territory to place reinforcements in
        :param armies: Number of armies to place
        :returns: True if placement successful, False otherwise
        """
        if not self.can_place_reinforcement(territory_id, armies):
            return False
        
        self.reinforcements_remaining -= armies
        self.placements_made.append((territory_id, armies))
        return True
    
    def undo_last_placement(self) -> Optional[Tuple[int, int]]:
        """
        Undo the last reinforcement placement. Restores reinforcements and 
        removes from placement history.
        
        :returns: Tuple of (territory_id, armies) that was undone, or None 
                 if no placements to undo
        """
        if not self.placements_made:
            return None
        
        territory_id, armies = self.placements_made.pop()
        self.reinforcements_remaining += armies
        return territory_id, armies
    
    def start_attack(self, attacker_territory: Territory, 
                    defender_territory: Territory) -> bool:
        """
        Start an attack between two territories. Validates attack conditions 
        and creates attack state.
        
        :param attacker_territory: Territory initiating the attack (must be 
                                  owned by current player)
        :param defender_territory: Territory being attacked (must not be 
                                  owned by current player)
        :returns: True if attack can start, False otherwise
        """
        if (self.phase != TurnPhase.ATTACKING or 
            self.current_attack is not None):
            return False
        
        # Validate attack conditions
        if (attacker_territory.armies <= 1 or  # Need armies to attack
            attacker_territory.owner != self.player_id or  # Must own attacker
            defender_territory.owner == self.player_id):   # Can't attack own territory
            return False
        
        # Check adjacency
        if defender_territory.id not in attacker_territory.adjacent_territories:
            return False
        
        self.current_attack = AttackState(
            attacker_territory_id=attacker_territory.id,
            defender_territory_id=defender_territory.id,
            max_attacking_armies=attacker_territory.armies - 1,  # Keep 1 army
            defending_armies=defender_territory.armies,
            attacking_armies=1
        )
        return True
    
    def resolve_attack(self) -> Optional[Dict]:
        """
        Resolve the current attack using the Fight system with dice-based 
        combat mechanics.
        
        :returns: Attack result dictionary with Fight results and territory 
                 status, or None if no active attack
        """
        if not self.current_attack or not self.current_attack.can_attack():
            return None
        
        # Create or continue existing fight
        if not self.current_fight:
            # Start new fight
            self.current_fight = Fight(
                attacker_territory_id=self.current_attack.attacker_territory_id,
                defender_territory_id=self.current_attack.defender_territory_id,
                initial_attackers=self.current_attack.attacking_armies,
                initial_defenders=self.current_attack.defending_armies
            )
        
        # Execute one round of combat
        try:
            dice_roll = self.current_fight.fight_round()
        except ValueError:
            # Fight cannot continue
            self.current_fight = None
            self.current_attack = None
            return None
        
        # Create result dictionary
        result = {
            'attacker_territory_id': self.current_attack.attacker_territory_id,
            'defender_territory_id': self.current_attack.defender_territory_id,
            'attacker_casualties': dice_roll.attacker_casualties,
            'defender_casualties': dice_roll.defender_casualties,
            'attacking_armies_before': self.current_attack.attacking_armies,
            'defending_armies_before': self.current_attack.defending_armies,
            'dice_roll': dice_roll,
            'fight_rounds': self.current_fight.rounds_fought,
            'total_attacker_casualties': self.current_fight.total_attacker_casualties,
            'total_defender_casualties': self.current_fight.total_defender_casualties
        }
        
        # Update attack state with casualties
        self.current_attack.max_attacking_armies -= dice_roll.attacker_casualties
        self.current_attack.defending_armies -= dice_roll.defender_casualties
        self.current_attack.attacking_armies = min(
            self.current_attack.attacking_armies - dice_roll.attacker_casualties,
            self.current_attack.max_attacking_armies
        )
        
        # Check if fight is complete
        if self.current_fight.is_completed():
            fight_result = self.current_fight.get_result()
            result['fight_result'] = fight_result
            result['fight_winner'] = self.current_fight.get_winner()
            result['fight_summary'] = self.current_fight.get_battle_summary()
            
            if fight_result == FightResult.ATTACKER_WINS:
                result['territory_conquered'] = True
                result['surviving_attackers'] = self.current_fight.current_attackers
            else:
                result['territory_conquered'] = False
                result['surviving_defenders'] = self.current_fight.current_defenders
            
            # End fight and attack
            self.current_fight = None
            self.current_attack = None
        else:
            result['territory_conquered'] = False
            result['fight_continues'] = True
        
        self.attacks_made += 1
        return result
    
    def end_attack(self) -> None:
        """
        End the current attack without resolution. Clears both attack and 
        fight states.
        """
        self.current_attack = None
        self.current_fight = None
    
    def start_movement(self, source_territory: Territory, 
                      target_territory: Territory) -> bool:
        """
        Start troop movement between owned territories. Validates movement 
        conditions and creates movement state.
        
        :param source_territory: Territory to move armies from (must be owned 
                                by current player)
        :param target_territory: Territory to move armies to (must be owned by 
                                current player and adjacent)
        :returns: True if movement can start, False otherwise
        """
        if (self.phase != TurnPhase.MOVING or 
            self.current_movement is not None):
            return False
        
        # Validate movement conditions
        if (source_territory.armies <= 1 or  # Need armies to move
            source_territory.owner != self.player_id or  # Must own source
            target_territory.owner != self.player_id):   # Must own target
            return False
        
        # Check adjacency
        if target_territory.id not in source_territory.adjacent_territories:
            return False
        
        self.current_movement = MovementState(
            source_territory_id=source_territory.id,
            target_territory_id=target_territory.id,
            max_moving_armies=source_territory.armies - 1,  # Keep 1 army
            moving_armies=1
        )
        return True
    
    def execute_movement(self) -> Optional[Dict]:
        """
        Execute the current movement. Moves armies between territories.
        
        :returns: Movement result dictionary with army transfer details, or 
                 None if no active movement
        """
        if not self.current_movement or not self.current_movement.can_move():
            return None
        
        result = {
            'source_territory_id': self.current_movement.source_territory_id,
            'target_territory_id': self.current_movement.target_territory_id,
            'armies_moved': self.current_movement.moving_armies,
        }
        
        self.movements_made += 1
        self.current_movement = None  # End movement
        return result
    
    def end_movement(self) -> None:
        """
        End the current movement without execution.
        """
        self.current_movement = None
    
    def advance_phase(self) -> bool:
        """
        Advance to the next phase of the turn. Validates phase transitions 
        and updates turn state.
        
        :returns: True if phase advanced, False if turn should end
        """
        if self.phase == TurnPhase.PLACEMENT:
            # Can only advance if all reinforcements are placed
            if self.reinforcements_remaining > 0:
                return False  # Still have reinforcements to place
            self.phase = TurnPhase.ATTACKING
            return True
        
        elif self.phase == TurnPhase.ATTACKING:
            # End any current attack
            self.end_attack()
            self.phase = TurnPhase.MOVING
            return True
        
        elif self.phase == TurnPhase.MOVING:
            # End any current movement - turn is complete
            self.end_movement()
            return False  # Turn ends
        
        return False


class TurnManager:
    """Manages turn progression and turn-specific game logic."""
    
    def __init__(self, game_state: GameState):
        """
        Initialize turn manager. Sets up turn state tracking for the given 
        game state.
        
        :param game_state: GameState to manage turns for
        """
        self.game_state = game_state
        self.current_turn: Optional[TurnState] = None
    
    def start_player_turn(self, player_id: int) -> bool:
        """
        Start a new turn for the specified player. Calculates reinforcements 
        and initializes turn state.
        
        :param player_id: ID of player whose turn is starting
        :returns: True if turn started successfully, False if player invalid
        """
        player = self.game_state.get_player(player_id)
        if not player or not player.is_active:
            return False
        
        # Calculate reinforcements for this turn
        reinforcements = self._calculate_reinforcements(player)
        
        # Create new turn state
        self.current_turn = TurnState(
            player_id=player_id,
            reinforcements_remaining=reinforcements
        )
        
        print(f"Starting turn for {player.name} - {reinforcements} reinforcements available")
        return True
    
    def _calculate_reinforcements(self, player: Player) -> int:
        """
        Calculate reinforcements for a player. Uses standard Risk rules: 
        max(3, territories_controlled // 3).
        
        :param player: Player to calculate reinforcements for
        :returns: Number of reinforcement armies the player receives
        """
        territory_count = player.get_territory_count()
        base_reinforcements = max(3, territory_count // 3)
        
        # TODO: Add continent bonuses in future
        # TODO: Add card bonuses in future
        
        return base_reinforcements
    
    def get_current_turn(self) -> Optional[TurnState]:
        """
        Get the current turn state.
        
        :returns: Current TurnState or None if no active turn
        """
        return self.current_turn
    
    def end_current_turn(self) -> bool:
        """
        End the current turn and advance to next player. Cleans up turn state 
        and advances game state.
        
        :returns: True if turn ended successfully, False if no active turn
        """
        if not self.current_turn:
            return False
        
        # Clean up any active actions
        if self.current_turn.current_attack:
            self.current_turn.end_attack()
        if self.current_turn.current_movement:
            self.current_turn.end_movement()
        
        # Clear turn state
        self.current_turn = None
        
        # Advance to next player in game state
        next_player_id = self.game_state.advance_turn()
        if next_player_id is None:
            # Game should end
            return False
        
        # Start next player's turn
        return self.start_player_turn(next_player_id)
    
    def is_turn_complete(self) -> bool:
        """
        Check if the current turn is complete. A turn is complete when all 
        phases are finished.
        
        :returns: True if current turn is complete and ready to end
        """
        if not self.current_turn:
            return True
        
        # Turn is complete when in MOVING phase and no active actions
        return (self.current_turn.phase == TurnPhase.MOVING and 
                self.current_turn.current_movement is None)
    
    def can_advance_phase(self) -> bool:
        """
        Check if the current phase can be advanced.
        
        :returns: True if phase can advance, False otherwise
        """
        if not self.current_turn:
            return False
        
        if self.current_turn.phase == TurnPhase.PLACEMENT:
            # Can advance if all reinforcements placed
            return self.current_turn.reinforcements_remaining == 0
        
        elif self.current_turn.phase == TurnPhase.ATTACKING:
            # Can always advance from attacking (end attacks)
            return True
        
        elif self.current_turn.phase == TurnPhase.MOVING:
            # Can advance to end turn (if no active movement)
            return self.current_turn.current_movement is None
        
        return False
    
    def advance_turn_phase(self) -> bool:
        """
        Advance the current turn to the next phase.
        
        :returns: True if phase advanced, False if turn should end
        """
        if not self.current_turn:
            return False
        
        return self.current_turn.advance_phase()