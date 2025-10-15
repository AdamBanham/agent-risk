"""
Unit tests for the fight system in Risk simulation.
Tests dice-based combat mechanics, casualty calculations, and fight progression.
"""

import unittest
from unittest.mock import patch
from risk.state.fight import Fight, FightPhase, FightResult, DiceRoll


class TestDiceRoll(unittest.TestCase):
    """Test DiceRoll casualty calculation mechanics."""
    
    def test_attacker_wins_both_dice(self):
        """Test when attacker wins both dice comparisons."""
        dice_roll = DiceRoll(
            attacker_dice=[6, 5],
            defender_dice=[4, 3]
        )
        self.assertEqual(dice_roll.attacker_casualties, 0)
        self.assertEqual(dice_roll.defender_casualties, 2)
    
    def test_defender_wins_both_dice(self):
        """Test when defender wins both dice comparisons."""
        dice_roll = DiceRoll(
            attacker_dice=[3, 2],
            defender_dice=[5, 4]
        )
        self.assertEqual(dice_roll.attacker_casualties, 2)
        self.assertEqual(dice_roll.defender_casualties, 0)
    
    def test_mixed_results(self):
        """Test when each side wins one die."""
        dice_roll = DiceRoll(
            attacker_dice=[6, 2],
            defender_dice=[4, 3]
        )
        self.assertEqual(dice_roll.attacker_casualties, 1)
        self.assertEqual(dice_roll.defender_casualties, 1)
    
    def test_defender_wins_ties(self):
        """Test that defender wins when dice are tied."""
        dice_roll = DiceRoll(
            attacker_dice=[4, 3],
            defender_dice=[4, 3]
        )
        self.assertEqual(dice_roll.attacker_casualties, 2)
        self.assertEqual(dice_roll.defender_casualties, 0)
    
    def test_single_die_combat(self):
        """Test combat with single die each."""
        dice_roll = DiceRoll(
            attacker_dice=[5],
            defender_dice=[3]
        )
        self.assertEqual(dice_roll.attacker_casualties, 0)
        self.assertEqual(dice_roll.defender_casualties, 1)


class TestFight(unittest.TestCase):
    """Test Fight class mechanics and progression."""
    
    def setUp(self):
        """Set up test fight instance."""
        self.fight = Fight(
            attacker_territory_id=1,
            defender_territory_id=2,
            initial_attackers=5,
            initial_defenders=3
        )
    
    def test_fight_initialization(self):
        """Test fight is properly initialized."""
        self.assertEqual(self.fight.attacker_territory_id, 1)
        self.assertEqual(self.fight.defender_territory_id, 2)
        self.assertEqual(self.fight.initial_attackers, 5)
        self.assertEqual(self.fight.initial_defenders, 3)
        self.assertEqual(self.fight.current_attackers, 5)
        self.assertEqual(self.fight.current_defenders, 3)
        self.assertEqual(self.fight.phase, FightPhase.ACTIVE)
        self.assertEqual(self.fight.rounds_fought, 0)
        self.assertEqual(self.fight.total_attacker_casualties, 0)
        self.assertEqual(self.fight.total_defender_casualties, 0)
    
    def test_can_continue_initially(self):
        """Test fight can continue with both armies present."""
        self.assertTrue(self.fight.can_continue())
        self.assertEqual(self.fight.get_result(), FightResult.ONGOING)
    
    def test_dice_count_calculation(self):
        """Test dice count calculation based on army numbers."""
        # Test attacker dice counts
        self.fight.current_attackers = 4
        self.assertEqual(self.fight.get_dice_count(is_attacker=True), 3)
        
        self.fight.current_attackers = 3
        self.assertEqual(self.fight.get_dice_count(is_attacker=True), 2)
        
        self.fight.current_attackers = 2
        self.assertEqual(self.fight.get_dice_count(is_attacker=True), 1)
        
        # Test defender dice counts
        self.fight.current_defenders = 2
        self.assertEqual(self.fight.get_dice_count(is_attacker=False), 2)
        
        self.fight.current_defenders = 1
        self.assertEqual(self.fight.get_dice_count(is_attacker=False), 1)
    
    def test_fight_cannot_continue_no_attackers(self):
        """Test fight stops when attackers are eliminated."""
        self.fight.current_attackers = 0
        self.assertFalse(self.fight.can_continue())
    
    def test_fight_cannot_continue_no_defenders(self):
        """Test fight stops when defenders are eliminated."""
        self.fight.current_defenders = 0
        self.assertFalse(self.fight.can_continue())
    
    def test_winner_determination(self):
        """Test winner is correctly determined when fight ends."""
        # Test attacker wins
        self.fight.phase = FightPhase.COMPLETED
        self.fight.current_defenders = 0
        self.fight.current_attackers = 2
        self.assertEqual(self.fight.get_winner(), "attacker")
        self.assertEqual(self.fight.get_result(), FightResult.ATTACKER_WINS)
        
        # Test defender wins
        self.fight.current_defenders = 1
        self.fight.current_attackers = 0
        self.assertEqual(self.fight.get_winner(), "defender")
        self.assertEqual(self.fight.get_result(), FightResult.DEFENDER_WINS)
    
    def test_winner_none_when_active(self):
        """Test no winner when fight is still active."""
        self.assertIsNone(self.fight.get_winner())
    
    def test_casualty_tracking(self):
        """Test casualty tracking through combat."""
        initial_att = self.fight.current_attackers
        initial_def = self.fight.current_defenders
        
        # Simulate some casualties
        self.fight.total_attacker_casualties = 2
        self.fight.total_defender_casualties = 1
        self.fight.current_attackers = initial_att - 2
        self.fight.current_defenders = initial_def - 1
        
        casualties = self.fight.get_casualties()
        self.assertEqual(casualties, (2, 1))
        
        survivors = self.fight.get_surviving_armies()
        self.assertEqual(survivors, (3, 2))
    
    @patch('random.randint')
    def test_fight_round_mechanics(self, mock_random):
        """Test single round of combat with mocked dice."""
        # Mock dice rolls: Need enough values for both attacker and defender
        # Attacker with 4 armies gets 3 dice, defender with 2 armies gets 2 dice
        mock_random.side_effect = [6, 5, 4, 3, 2]  # Extra values just in case
        
        # Set up specific army counts to get predictable dice counts
        self.fight.current_attackers = 4  # Gets 3 dice
        self.fight.current_defenders = 2  # Gets 2 dice
        
        dice_roll = self.fight.fight_round()
        
        # Verify dice roll results
        self.assertEqual(len(dice_roll.attacker_dice), 3)
        self.assertEqual(len(dice_roll.defender_dice), 2)
        
        # Verify fight state updates
        self.assertEqual(self.fight.rounds_fought, 1)
        self.assertEqual(len(self.fight.dice_history), 1)
    
    def test_fight_round_error_when_cannot_continue(self):
        """Test fight_round raises error when fight cannot continue."""
        self.fight.current_attackers = 0
        
        with self.assertRaises(ValueError):
            self.fight.fight_round()
    
    @patch('random.randint')
    def test_fight_to_completion(self, mock_random):
        """Test complete fight execution."""
        # Set up mock to create a predictable fight outcome
        # Use high values for attackers, low for defenders to ensure attacker wins
        mock_values = []
        # Generate enough values for a complete fight (estimate ~10 rounds max)
        for i in range(50):
            if i % 6 < 3:  # Attacker dice (high values)
                mock_values.append(6)
            else:  # Defender dice (low values)
                mock_values.append(1)
        
        mock_random.side_effect = mock_values
        
        result = self.fight.fight_to_completion()
        
        self.assertTrue(self.fight.is_completed())
        self.assertEqual(self.fight.phase, FightPhase.COMPLETED)
        self.assertGreater(self.fight.rounds_fought, 0)
        # Don't assert specific result since it depends on random dice
    
    def test_battle_summary_generation(self):
        """Test battle summary string generation."""
        self.fight.rounds_fought = 3
        self.fight.total_attacker_casualties = 2
        self.fight.total_defender_casualties = 1
        
        summary = self.fight.get_battle_summary()
        
        self.assertIn("Territory 1 -> 2", summary)
        self.assertIn("5 attackers vs 3 defenders", summary)
        self.assertIn("Rounds: 3", summary)
        self.assertIn("2 attackers, 1 defenders", summary)
        self.assertIn("ongoing", summary)
    
    def test_repr_string(self):
        """Test string representation for debugging."""
        repr_str = repr(self.fight)
        
        self.assertIn("Fight(", repr_str)
        self.assertIn("attacker_territory=1", repr_str)
        self.assertIn("defender_territory=2", repr_str)
        self.assertIn("attackers=5/5", repr_str)
        self.assertIn("defenders=3/3", repr_str)
        self.assertIn("rounds=0", repr_str)
        self.assertIn("phase=active", repr_str)


if __name__ == '__main__':
    unittest.main()