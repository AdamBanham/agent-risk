"""
Fight data structures for the Risk simulation.
Represents contested territory battles with dice-based combat mechanics.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import random


class FightPhase(Enum):
    """Possible phases of a fight."""
    ACTIVE = "active"        # Fight is ongoing
    COMPLETED = "completed"  # Fight has ended with a winner


class FightResult(Enum):
    """Possible outcomes of a fight."""
    ATTACKER_WINS = "attacker_wins"    # Attacker conquers territory
    DEFENDER_WINS = "defender_wins"    # Defender retains territory
    ONGOING = "ongoing"                # Fight continues

    def attacker_won(self) -> bool:
        """Check if the attacker won the fight."""
        return self == FightResult.ATTACKER_WINS
    
    def defender_won(self) -> bool:
        """Check if the defender won the fight."""
        return self == FightResult.DEFENDER_WINS
    
    def is_ongoing(self) -> bool:
        """Check if the fight is still ongoing."""
        return self == FightResult.ONGOING


@dataclass
class DiceRoll:
    """Represents a single dice roll in combat."""
    attacker_dice: List[int] = field(default_factory=list)
    defender_dice: List[int] = field(default_factory=list)
    attacker_casualties: int = 0
    defender_casualties: int = 0
    
    def __post_init__(self):
        """Calculate casualties based on dice results after initialization."""
        if self.attacker_dice and self.defender_dice:
            self._calculate_casualties()
    
    def _calculate_casualties(self) -> None:
        """
        Calculate casualties based on dice roll results. Higher dice win 
        battles, ties go to defender.
        """
        # Sort dice in descending order for comparison
        attacker_sorted = sorted(self.attacker_dice, reverse=True)
        defender_sorted = sorted(self.defender_dice, reverse=True)
        
        # Compare dice pairwise (highest vs highest, etc.)
        battles = min(len(attacker_sorted), len(defender_sorted))
        
        for i in range(battles):
            if attacker_sorted[i] > defender_sorted[i]:
                self.defender_casualties += 1
            else:  # Defender wins ties
                self.attacker_casualties += 1


@dataclass
class Fight:
    """
    Represents a fight between attacking and defending armies. Manages 
    dice-based combat with casualty tracking.
    """
    attacker_territory_id: int
    defender_territory_id: int
    initial_attackers: int
    initial_defenders: int
    
    # Current army counts
    current_attackers: int = field(init=False)
    current_defenders: int = field(init=False)
    
    # Fight tracking
    phase: FightPhase = FightPhase.ACTIVE
    rounds_fought: int = 0
    total_attacker_casualties: int = 0
    total_defender_casualties: int = 0
    dice_history: List[DiceRoll] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize current army counts after object creation."""
        self.current_attackers = self.initial_attackers
        self.current_defenders = self.initial_defenders
    
    def get_dice_count(self, is_attacker: bool) -> int:
        """
        Determine number of dice to roll based on army count. Follows Risk 
        combat rules for dice allocation.
        
        :param is_attacker: True for attacker, False for defender
        :returns: Number of dice to roll (1-3 for attacker, 1-2 for defender)
        """
        if is_attacker:
            # Attacker can roll 1-3 dice based on army count
            if self.current_attackers >= 4:
                return 3
            elif self.current_attackers >= 3:
                return 2
            else:
                return 1
        else:
            # Defender can roll 1-2 dice based on army count
            if self.current_defenders >= 2:
                return 2
            else:
                return 1
    
    def roll_dice(self) -> List[int]:
        """
        Roll a set of 6-sided dice. Each die shows values 1-6.
        
        :returns: List of dice values in random order
        """
        return [random.randint(1, 6)]
    
    def fight_round(self) -> DiceRoll:
        """
        Execute a single round of combat. Rolls dice for both sides and 
        calculates casualties.
        
        :returns: DiceRoll object containing results of this combat round
        :raises ValueError: When fight cannot continue (no valid armies)
        """
        if not self.can_continue():
            raise ValueError("Fight cannot continue - insufficient armies")
        
        # Determine dice counts
        attacker_dice_count = self.get_dice_count(is_attacker=True)
        defender_dice_count = self.get_dice_count(is_attacker=False)
        
        # Roll dice for both sides
        attacker_dice = [random.randint(1, 6) for _ in range(attacker_dice_count)]
        defender_dice = [random.randint(1, 6) for _ in range(defender_dice_count)]
        
        # Create dice roll result and calculate casualties
        dice_roll = DiceRoll(
            attacker_dice=attacker_dice,
            defender_dice=defender_dice
        )
        
        # Apply casualties
        self.current_attackers -= dice_roll.attacker_casualties
        self.current_defenders -= dice_roll.defender_casualties
        self.total_attacker_casualties += dice_roll.attacker_casualties
        self.total_defender_casualties += dice_roll.defender_casualties
        
        # Update fight state
        self.rounds_fought += 1
        self.dice_history.append(dice_roll)
        
        # Check if fight is complete
        if not self.can_continue():
            self.phase = FightPhase.COMPLETED
        
        return dice_roll
    
    def can_continue(self) -> bool:
        """
        Check if the fight can continue. Requires both attackers and 
        defenders with valid army counts.
        
        :returns: True if fight can continue, False if one side is eliminated
        """
        return (self.current_attackers > 0 and 
                self.current_defenders > 0 and 
                self.phase == FightPhase.ACTIVE)
    
    def get_winner(self) -> Optional[str]:
        """
        Determine the winner of the fight. Only valid when fight is completed.
        
        :returns: "attacker" if attacker wins, "defender" if defender wins, 
                 None if fight is ongoing
        """
        if self.phase != FightPhase.COMPLETED:
            return None
        
        if self.current_defenders == 0:
            return "attacker"
        elif self.current_attackers == 0:
            return "defender"
        else:
            return None  # Should not happen in normal gameplay
    
    def get_result(self) -> FightResult:
        """
        Get the current result of the fight. Indicates fight outcome or 
        ongoing status.
        
        :returns: FightResult enum indicating current fight status
        """
        if self.phase == FightPhase.ACTIVE:
            return FightResult.ONGOING
        
        winner = self.get_winner()
        if winner == "attacker":
            return FightResult.ATTACKER_WINS
        elif winner == "defender":
            return FightResult.DEFENDER_WINS
        else:
            return FightResult.ONGOING
    
    def get_surviving_armies(self) -> Tuple[int, int]:
        """
        Get the current army counts for both sides. Returns surviving armies 
        after all combat rounds.
        
        :returns: Tuple of (surviving_attackers, surviving_defenders)
        """
        return (self.current_attackers, self.current_defenders)
    
    def get_casualties(self) -> Tuple[int, int]:
        """
        Get total casualties for both sides. Returns cumulative losses 
        throughout the fight.
        
        :returns: Tuple of (attacker_casualties, defender_casualties)
        """
        return (self.total_attacker_casualties, self.total_defender_casualties)
    
    def fight_to_completion(self) -> FightResult:
        """
        Execute the entire fight until completion. Continues rolling dice 
        until one side is eliminated.
        
        :returns: Final result of the completed fight
        """
        while self.can_continue():
            self.fight_round()
        
        return self.get_result()
    
    def is_completed(self) -> bool:
        """
        Check if the fight has been completed. Fight is complete when one 
        side is eliminated.
        
        :returns: True if fight is finished, False if ongoing
        """
        return self.phase == FightPhase.COMPLETED
    
    def get_battle_summary(self) -> str:
        """
        Generate a human-readable summary of the fight results. Includes 
        army counts, casualties, and outcome.
        
        :returns: String summary of the fight for display or logging
        """
        result = self.get_result()
        casualties_att, casualties_def = self.get_casualties()
        
        summary = (
            f"Fight: Territory {self.attacker_territory_id} -> "
            f"{self.defender_territory_id}\n"
            f"Initial: {self.initial_attackers} attackers vs "
            f"{self.initial_defenders} defenders\n"
            f"Rounds: {self.rounds_fought}\n"
            f"Casualties: {casualties_att} attackers, {casualties_def} defenders\n"
            f"Result: {result.value}"
        )
        
        if self.is_completed():
            winner = self.get_winner()
            survivors_att, survivors_def = self.get_surviving_armies()
            summary += f"\nWinner: {winner}\n"
            summary += f"Survivors: {survivors_att} attackers, {survivors_def} defenders"
        
        return summary
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"Fight(attacker_territory={self.attacker_territory_id}, "
                f"defender_territory={self.defender_territory_id}, "
                f"attackers={self.current_attackers}/{self.initial_attackers}, "
                f"defenders={self.current_defenders}/{self.initial_defenders}, "
                f"rounds={self.rounds_fought}, phase={self.phase.value})")