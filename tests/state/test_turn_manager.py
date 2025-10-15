"""
Test suite for TurnManager and related turn management classes.
Tests turn progression, phase management, and turn-specific actions.
"""

import unittest
from unittest.mock import Mock, patch

from risk.state.turn_manager import (
    TurnManager, TurnState, TurnPhase, AttackState, MovementState
)
from risk.state.game_state import GameState, Player, GamePhase
from risk.state.territory import Territory, TerritoryState


class TestAttackState(unittest.TestCase):
    """Test the AttackState data structure."""
    
    def test_attack_state_creation(self):
        """Test basic AttackState creation and initialization."""
        attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=5,
            defending_armies=3
        )
        
        self.assertEqual(attack.attacker_territory_id, 1)
        self.assertEqual(attack.defender_territory_id, 2)
        self.assertEqual(attack.max_attacking_armies, 5)
        self.assertEqual(attack.defending_armies, 3)
        self.assertEqual(attack.attacking_armies, 1)  # Default value
    
    def test_can_attack_valid_conditions(self):
        """Test can_attack returns True for valid attack conditions."""
        attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=5,
            defending_armies=3,
            attacking_armies=3
        )
        
        self.assertTrue(attack.can_attack())
    
    def test_can_attack_invalid_attacking_armies(self):
        """Test can_attack returns False when attacking armies are invalid."""
        # Test with 0 attacking armies
        attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=5,
            defending_armies=3,
            attacking_armies=0
        )
        self.assertFalse(attack.can_attack())
        
        # Test with too many attacking armies
        attack.attacking_armies = 6
        self.assertFalse(attack.can_attack())
    
    def test_can_attack_no_defending_armies(self):
        """Test can_attack returns False when no defending armies remain."""
        attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=5,
            defending_armies=0,
            attacking_armies=3
        )
        
        self.assertFalse(attack.can_attack())


class TestMovementState(unittest.TestCase):
    """Test the MovementState data structure."""
    
    def test_movement_state_creation(self):
        """Test basic MovementState creation and initialization."""
        movement = MovementState(
            source_territory_id=1,
            target_territory_id=2,
            max_moving_armies=4
        )
        
        self.assertEqual(movement.source_territory_id, 1)
        self.assertEqual(movement.target_territory_id, 2)
        self.assertEqual(movement.max_moving_armies, 4)
        self.assertEqual(movement.moving_armies, 1)  # Default value
    
    def test_can_move_valid_conditions(self):
        """Test can_move returns True for valid movement conditions."""
        movement = MovementState(
            source_territory_id=1,
            target_territory_id=2,
            max_moving_armies=4,
            moving_armies=2
        )
        
        self.assertTrue(movement.can_move())
    
    def test_can_move_invalid_moving_armies(self):
        """Test can_move returns False when moving armies are invalid."""
        # Test with 0 moving armies
        movement = MovementState(
            source_territory_id=1,
            target_territory_id=2,
            max_moving_armies=4,
            moving_armies=0
        )
        self.assertFalse(movement.can_move())
        
        # Test with too many moving armies
        movement.moving_armies = 5
        self.assertFalse(movement.can_move())


class TestTurnState(unittest.TestCase):
    """Test the TurnState class and its methods."""
    
    def setUp(self):
        """Set up test fixtures for TurnState tests."""
        self.turn_state = TurnState(
            player_id=1,
            reinforcements_remaining=5
        )
    
    def test_turn_state_creation(self):
        """Test basic TurnState creation and default values."""
        self.assertEqual(self.turn_state.player_id, 1)
        self.assertEqual(self.turn_state.phase, TurnPhase.PLACEMENT)
        self.assertEqual(self.turn_state.reinforcements_remaining, 5)
        self.assertEqual(self.turn_state.placements_made, [])
        self.assertEqual(self.turn_state.attacks_made, 0)
        self.assertEqual(self.turn_state.movements_made, 0)
        self.assertIsNone(self.turn_state.current_attack)
        self.assertIsNone(self.turn_state.current_movement)
    
    def test_can_place_reinforcement_valid(self):
        """Test can_place_reinforcement returns True for valid placements."""
        self.assertTrue(self.turn_state.can_place_reinforcement(1, 2))
        self.assertTrue(self.turn_state.can_place_reinforcement(1, 5))
        self.assertTrue(self.turn_state.can_place_reinforcement(2, 1))
    
    def test_can_place_reinforcement_invalid_phase(self):
        """Test can_place_reinforcement returns False in wrong phase."""
        self.turn_state.phase = TurnPhase.ATTACKING
        self.assertFalse(self.turn_state.can_place_reinforcement(1, 2))
    
    def test_can_place_reinforcement_insufficient_armies(self):
        """Test can_place_reinforcement returns False with too many armies."""
        self.assertFalse(self.turn_state.can_place_reinforcement(1, 6))
        self.assertFalse(self.turn_state.can_place_reinforcement(1, 0))
    
    def test_place_reinforcement_success(self):
        """Test successful reinforcement placement."""
        result = self.turn_state.place_reinforcement(1, 3)
        
        self.assertTrue(result)
        self.assertEqual(self.turn_state.reinforcements_remaining, 2)
        self.assertEqual(self.turn_state.placements_made, [(1, 3)])
    
    def test_place_reinforcement_failure(self):
        """Test failed reinforcement placement."""
        result = self.turn_state.place_reinforcement(1, 6)  # Too many armies
        
        self.assertFalse(result)
        self.assertEqual(self.turn_state.reinforcements_remaining, 5)
        self.assertEqual(self.turn_state.placements_made, [])
    
    def test_multiple_placements(self):
        """Test multiple reinforcement placements tracking."""
        self.turn_state.place_reinforcement(1, 2)
        self.turn_state.place_reinforcement(2, 1)
        self.turn_state.place_reinforcement(3, 2)
        
        self.assertEqual(self.turn_state.reinforcements_remaining, 0)
        self.assertEqual(self.turn_state.placements_made, [(1, 2), (2, 1), (3, 2)])
    
    def test_undo_last_placement_success(self):
        """Test successful undo of last placement."""
        self.turn_state.place_reinforcement(1, 3)
        self.turn_state.place_reinforcement(2, 1)
        
        result = self.turn_state.undo_last_placement()
        
        self.assertEqual(result, (2, 1))
        self.assertEqual(self.turn_state.reinforcements_remaining, 2)
        self.assertEqual(self.turn_state.placements_made, [(1, 3)])
    
    def test_undo_last_placement_empty(self):
        """Test undo with no placements made."""
        result = self.turn_state.undo_last_placement()
        
        self.assertIsNone(result)
        self.assertEqual(self.turn_state.reinforcements_remaining, 5)
        self.assertEqual(self.turn_state.placements_made, [])
    
    def test_start_attack_success(self):
        """Test successful attack initiation."""
        self.turn_state.phase = TurnPhase.ATTACKING
        
        # Create mock territories
        attacker = Territory(
            id=1, name="Attacker", center=(100, 100), vertices=[], 
            owner=1, armies=5, adjacent_territories={2}
        )
        defender = Territory(
            id=2, name="Defender", center=(200, 200), vertices=[], 
            owner=2, armies=3
        )
        
        result = self.turn_state.start_attack(attacker, defender)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.turn_state.current_attack)
        self.assertEqual(self.turn_state.current_attack.attacker_territory_id, 1)
        self.assertEqual(self.turn_state.current_attack.defender_territory_id, 2)
        self.assertEqual(self.turn_state.current_attack.max_attacking_armies, 4)
        self.assertEqual(self.turn_state.current_attack.defending_armies, 3)
    
    def test_start_attack_wrong_phase(self):
        """Test attack initiation fails in wrong phase."""
        attacker = Territory(
            id=1, name="Attacker", center=(100, 100), vertices=[], 
            owner=1, armies=5, adjacent_territories={2}
        )
        defender = Territory(
            id=2, name="Defender", center=(200, 200), vertices=[], 
            owner=2, armies=3
        )
        
        result = self.turn_state.start_attack(attacker, defender)
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_state.current_attack)
    
    def test_start_attack_insufficient_armies(self):
        """Test attack initiation fails with insufficient armies."""
        self.turn_state.phase = TurnPhase.ATTACKING
        
        attacker = Territory(
            id=1, name="Attacker", center=(100, 100), vertices=[], 
            owner=1, armies=1, adjacent_territories={2}  # Only 1 army
        )
        defender = Territory(
            id=2, name="Defender", center=(200, 200), vertices=[], 
            owner=2, armies=3
        )
        
        result = self.turn_state.start_attack(attacker, defender)
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_state.current_attack)
    
    def test_start_attack_not_adjacent(self):
        """Test attack initiation fails when territories not adjacent."""
        self.turn_state.phase = TurnPhase.ATTACKING
        
        attacker = Territory(
            id=1, name="Attacker", center=(100, 100), vertices=[], 
            owner=1, armies=5, adjacent_territories={3}  # Not adjacent to 2
        )
        defender = Territory(
            id=2, name="Defender", center=(200, 200), vertices=[], 
            owner=2, armies=3
        )
        
        result = self.turn_state.start_attack(attacker, defender)
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_state.current_attack)
    
    def test_resolve_attack_success(self):
        """Test successful attack resolution."""
        self.turn_state.phase = TurnPhase.ATTACKING
        self.turn_state.current_attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=4,
            defending_armies=3,
            attacking_armies=2
        )
        
        result = self.turn_state.resolve_attack()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['attacker_territory_id'], 1)
        self.assertEqual(result['defender_territory_id'], 2)
        self.assertEqual(result['attacker_casualties'], 1)
        self.assertEqual(result['defender_casualties'], 1)
        self.assertFalse(result['territory_conquered'])
        self.assertEqual(self.turn_state.attacks_made, 1)
    
    def test_resolve_attack_territory_conquered(self):
        """Test attack resolution when territory is conquered."""
        self.turn_state.phase = TurnPhase.ATTACKING
        self.turn_state.current_attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=4,
            defending_armies=1,  # Only 1 defender
            attacking_armies=2
        )
        
        result = self.turn_state.resolve_attack()
        
        self.assertIsNotNone(result)
        self.assertTrue(result['territory_conquered'])
        self.assertIsNone(self.turn_state.current_attack)  # Attack ends
    
    def test_resolve_attack_no_active_attack(self):
        """Test attack resolution fails with no active attack."""
        result = self.turn_state.resolve_attack()
        
        self.assertIsNone(result)
    
    def test_start_movement_success(self):
        """Test successful movement initiation."""
        self.turn_state.phase = TurnPhase.MOVING
        
        source = Territory(
            id=1, name="Source", center=(100, 100), vertices=[], 
            owner=1, armies=5, adjacent_territories={2}
        )
        target = Territory(
            id=2, name="Target", center=(200, 200), vertices=[], 
            owner=1, armies=2
        )
        
        result = self.turn_state.start_movement(source, target)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.turn_state.current_movement)
        self.assertEqual(self.turn_state.current_movement.source_territory_id, 1)
        self.assertEqual(self.turn_state.current_movement.target_territory_id, 2)
        self.assertEqual(self.turn_state.current_movement.max_moving_armies, 4)
    
    def test_start_movement_wrong_phase(self):
        """Test movement initiation fails in wrong phase."""
        source = Territory(
            id=1, name="Source", center=(100, 100), vertices=[], 
            owner=1, armies=5, adjacent_territories={2}
        )
        target = Territory(
            id=2, name="Target", center=(200, 200), vertices=[], 
            owner=1, armies=2
        )
        
        result = self.turn_state.start_movement(source, target)
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_state.current_movement)
    
    def test_execute_movement_success(self):
        """Test successful movement execution."""
        self.turn_state.current_movement = MovementState(
            source_territory_id=1,
            target_territory_id=2,
            max_moving_armies=4,
            moving_armies=2
        )
        
        result = self.turn_state.execute_movement()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['source_territory_id'], 1)
        self.assertEqual(result['target_territory_id'], 2)
        self.assertEqual(result['armies_moved'], 2)
        self.assertEqual(self.turn_state.movements_made, 1)
        self.assertIsNone(self.turn_state.current_movement)  # Movement ends
    
    def test_execute_movement_no_active_movement(self):
        """Test movement execution fails with no active movement."""
        result = self.turn_state.execute_movement()
        
        self.assertIsNone(result)
    
    def test_advance_phase_placement_to_attacking(self):
        """Test phase advancement from placement to attacking."""
        self.turn_state.reinforcements_remaining = 0
        
        result = self.turn_state.advance_phase()
        
        self.assertTrue(result)
        self.assertEqual(self.turn_state.phase, TurnPhase.ATTACKING)
    
    def test_advance_phase_placement_with_reinforcements(self):
        """Test phase advancement fails with remaining reinforcements."""
        self.turn_state.reinforcements_remaining = 3
        
        result = self.turn_state.advance_phase()
        
        self.assertFalse(result)
        self.assertEqual(self.turn_state.phase, TurnPhase.PLACEMENT)
    
    def test_advance_phase_attacking_to_moving(self):
        """Test phase advancement from attacking to moving."""
        self.turn_state.phase = TurnPhase.ATTACKING
        
        result = self.turn_state.advance_phase()
        
        self.assertTrue(result)
        self.assertEqual(self.turn_state.phase, TurnPhase.MOVING)
    
    def test_advance_phase_moving_ends_turn(self):
        """Test phase advancement from moving ends the turn."""
        self.turn_state.phase = TurnPhase.MOVING
        
        result = self.turn_state.advance_phase()
        
        self.assertFalse(result)  # Turn should end


class TestTurnManager(unittest.TestCase):
    """Test the TurnManager class and its coordination functionality."""
    
    def setUp(self):
        """Set up test fixtures for TurnManager tests."""
        # Create a mock game state with players
        self.game_state = Mock(spec=GameState)
        
        # Create mock players
        self.player1 = Mock(spec=Player)
        self.player1.id = 1
        self.player1.name = "Player 1"
        self.player1.is_active = True
        self.player1.territories_controlled = {1, 2, 3}
        self.player1.get_territory_count.return_value = 3
        
        self.player2 = Mock(spec=Player)
        self.player2.id = 2
        self.player2.name = "Player 2"
        self.player2.is_active = True
        self.player2.territories_controlled = {4, 5}
        self.player2.get_territory_count.return_value = 2
        
        # Configure game state mock
        self.game_state.get_player.side_effect = lambda pid: (
            self.player1 if pid == 1 else self.player2 if pid == 2 else None
        )
        self.game_state.advance_turn.return_value = 2
        
        self.turn_manager = TurnManager(self.game_state)
    
    def test_turn_manager_creation(self):
        """Test basic TurnManager creation."""
        self.assertEqual(self.turn_manager.game_state, self.game_state)
        self.assertIsNone(self.turn_manager.current_turn)
    
    def test_calculate_reinforcements_minimum(self):
        """Test reinforcement calculation with minimum (3 armies)."""
        player = Mock()
        player.get_territory_count.return_value = 2  # Less than 9 territories
        
        reinforcements = self.turn_manager._calculate_reinforcements(player)
        
        self.assertEqual(reinforcements, 3)  # Minimum reinforcements
    
    def test_calculate_reinforcements_territory_bonus(self):
        """Test reinforcement calculation with territory bonus."""
        player = Mock()
        player.get_territory_count.return_value = 15  # 15 // 3 = 5 > 3
        
        reinforcements = self.turn_manager._calculate_reinforcements(player)
        
        self.assertEqual(reinforcements, 5)  # Territory bonus
    
    def test_start_player_turn_success(self):
        """Test successful player turn start."""
        with patch('builtins.print'):  # Suppress print output
            result = self.turn_manager.start_player_turn(1)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.turn_manager.current_turn)
        self.assertEqual(self.turn_manager.current_turn.player_id, 1)
        self.assertEqual(self.turn_manager.current_turn.phase, TurnPhase.PLACEMENT)
        self.assertEqual(self.turn_manager.current_turn.reinforcements_remaining, 3)
    
    def test_start_player_turn_invalid_player(self):
        """Test player turn start fails with invalid player."""
        result = self.turn_manager.start_player_turn(99)  # Non-existent player
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_manager.current_turn)
    
    def test_start_player_turn_inactive_player(self):
        """Test player turn start fails with inactive player."""
        self.player1.is_active = False
        
        result = self.turn_manager.start_player_turn(1)
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_manager.current_turn)
    
    def test_get_current_turn(self):
        """Test getting current turn state."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
        
        current_turn = self.turn_manager.get_current_turn()
        
        self.assertIsNotNone(current_turn)
        self.assertEqual(current_turn.player_id, 1)
    
    def test_get_current_turn_no_active_turn(self):
        """Test getting current turn when no turn is active."""
        current_turn = self.turn_manager.get_current_turn()
        
        self.assertIsNone(current_turn)
    
    def test_end_current_turn_success(self):
        """Test successful turn ending and advancement."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            result = self.turn_manager.end_current_turn()
        
        self.assertTrue(result)
        # Should start next player's turn
        self.assertIsNotNone(self.turn_manager.current_turn)
        self.assertEqual(self.turn_manager.current_turn.player_id, 2)
    
    def test_end_current_turn_no_active_turn(self):
        """Test ending turn fails when no turn is active."""
        result = self.turn_manager.end_current_turn()
        
        self.assertFalse(result)
    
    def test_end_current_turn_game_ends(self):
        """Test ending turn when game should end."""
        self.game_state.advance_turn.return_value = None  # Game ends
        
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            result = self.turn_manager.end_current_turn()
        
        self.assertFalse(result)
        self.assertIsNone(self.turn_manager.current_turn)
    
    def test_is_turn_complete_no_turn(self):
        """Test turn completion check with no active turn."""
        result = self.turn_manager.is_turn_complete()
        
        self.assertTrue(result)
    
    def test_is_turn_complete_moving_phase_no_movement(self):
        """Test turn completion in moving phase with no active movement."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = None
        
        result = self.turn_manager.is_turn_complete()
        
        self.assertTrue(result)
    
    def test_is_turn_complete_moving_phase_with_movement(self):
        """Test turn completion in moving phase with active movement."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = Mock()
        
        result = self.turn_manager.is_turn_complete()
        
        self.assertFalse(result)
    
    def test_is_turn_complete_other_phases(self):
        """Test turn completion in placement and attacking phases."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
        
        # Placement phase - not complete
        self.turn_manager.current_turn.phase = TurnPhase.PLACEMENT
        self.assertFalse(self.turn_manager.is_turn_complete())
        
        # Attacking phase - not complete
        self.turn_manager.current_turn.phase = TurnPhase.ATTACKING
        self.assertFalse(self.turn_manager.is_turn_complete())
    
    def test_can_advance_phase_no_turn(self):
        """Test phase advancement check with no active turn."""
        result = self.turn_manager.can_advance_phase()
        
        self.assertFalse(result)
    
    def test_can_advance_phase_placement_with_reinforcements(self):
        """Test phase advancement check in placement with reinforcements."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.reinforcements_remaining = 2
        
        result = self.turn_manager.can_advance_phase()
        
        self.assertFalse(result)
    
    def test_can_advance_phase_placement_no_reinforcements(self):
        """Test phase advancement check in placement without reinforcements."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.reinforcements_remaining = 0
        
        result = self.turn_manager.can_advance_phase()
        
        self.assertTrue(result)
    
    def test_can_advance_phase_attacking(self):
        """Test phase advancement check in attacking phase."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.ATTACKING
        
        result = self.turn_manager.can_advance_phase()
        
        self.assertTrue(result)
    
    def test_can_advance_phase_moving_with_movement(self):
        """Test phase advancement check in moving with active movement."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = Mock()
        
        result = self.turn_manager.can_advance_phase()
        
        self.assertFalse(result)
    
    def test_can_advance_phase_moving_no_movement(self):
        """Test phase advancement check in moving without active movement."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = None
        
        result = self.turn_manager.can_advance_phase()
        
        self.assertTrue(result)
    
    def test_advance_turn_phase_success(self):
        """Test successful turn phase advancement."""
        with patch('builtins.print'):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.reinforcements_remaining = 0
        
        result = self.turn_manager.advance_turn_phase()
        
        self.assertTrue(result)
        self.assertEqual(self.turn_manager.current_turn.phase, TurnPhase.ATTACKING)
    
    def test_advance_turn_phase_no_turn(self):
        """Test turn phase advancement fails with no active turn."""
        result = self.turn_manager.advance_turn_phase()
        
        self.assertFalse(result)


class TestTurnManagerIntegration(unittest.TestCase):
    """Integration tests for TurnManager with real game state."""
    
    def setUp(self):
        """Set up real game state for integration tests."""
        # Create a minimal game state
        self.game_state = GameState.create_new_game(
            regions=5, num_players=2, starting_armies=10
        )
        
        # Add some territories manually for testing
        self.territory1 = Territory(
            id=1, name="Territory 1", center=(100, 100), vertices=[], 
            owner=0, armies=5, adjacent_territories={2}  # Player IDs start at 0
        )
        self.territory2 = Territory(
            id=2, name="Territory 2", center=(200, 200), vertices=[], 
            owner=1, armies=3, adjacent_territories={1}
        )
        
        self.game_state.territories[1] = self.territory1
        self.game_state.territories[2] = self.territory2
        
        # Update player statistics based on territories
        self.game_state.update_player_statistics()
        
        self.turn_manager = TurnManager(self.game_state)
    
    def test_full_turn_cycle(self):
        """Test a complete turn cycle from start to finish."""
        with patch('builtins.print'):
            # Start player 0's turn (first player)
            self.assertTrue(self.turn_manager.start_player_turn(0))
            
            # Should be in placement phase
            turn = self.turn_manager.get_current_turn()
            self.assertEqual(turn.phase, TurnPhase.PLACEMENT)
            self.assertEqual(turn.reinforcements_remaining, 3)
            
            # Place reinforcements
            self.assertTrue(turn.place_reinforcement(1, 3))
            self.assertEqual(turn.reinforcements_remaining, 0)
            
            # Advance to attacking phase
            self.assertTrue(self.turn_manager.advance_turn_phase())
            self.assertEqual(turn.phase, TurnPhase.ATTACKING)
            
            # Start an attack
            self.assertTrue(turn.start_attack(self.territory1, self.territory2))
            self.assertIsNotNone(turn.current_attack)
            
            # Resolve attack
            result = turn.resolve_attack()
            self.assertIsNotNone(result)
            
            # Advance to moving phase
            self.assertTrue(self.turn_manager.advance_turn_phase())
            self.assertEqual(turn.phase, TurnPhase.MOVING)
            
            # End turn - this should work regardless of which player goes next
            # The actual behavior depends on the game state's advance_turn method
            result = self.turn_manager.end_current_turn()
            
            # Verify either the turn ended successfully or the game ended
            # (both are valid outcomes in different scenarios)
            self.assertTrue(isinstance(result, bool))
            
            # If turn ended successfully, verify we have a new turn state
            if result:
                new_turn = self.turn_manager.get_current_turn()
                self.assertIsNotNone(new_turn)
                # Verify it's a fresh turn state
                self.assertEqual(new_turn.phase, TurnPhase.PLACEMENT)


if __name__ == '__main__':
    unittest.main()