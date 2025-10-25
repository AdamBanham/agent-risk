"""
Test suite for TurnManager and related turn management classes.
Tests turn progression, phase management, and turn-specific actions.
"""

import unittest
from unittest.mock import Mock, patch

from risk.state.turn_manager import (
    TurnManager,
    TurnPhase,
    AttackState,
    MovementState,
)
from risk.state.game_state import GameState, Player


class TestAttackState(unittest.TestCase):
    """Test the AttackState data structure."""

    def test_attack_state_creation(self):
        """Test basic AttackState creation and initialization."""
        attack = AttackState(
            attacker_territory_id=1,
            defender_territory_id=2,
            max_attacking_armies=5,
            defending_armies=3,
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
            attacking_armies=3,
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
            attacking_armies=0,
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
            attacking_armies=3,
        )

        self.assertFalse(attack.can_attack())


class TestMovementState(unittest.TestCase):
    """Test the MovementState data structure."""

    def test_movement_state_creation(self):
        """Test basic MovementState creation and initialization."""
        movement = MovementState(
            source_territory_id=1, target_territory_id=2, max_moving_armies=4
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
            moving_armies=2,
        )

        self.assertTrue(movement.can_move())

    def test_can_move_invalid_moving_armies(self):
        """Test can_move returns False when moving armies are invalid."""
        # Test with 0 moving armies
        movement = MovementState(
            source_territory_id=1,
            target_territory_id=2,
            max_moving_armies=4,
            moving_armies=0,
        )
        self.assertFalse(movement.can_move())

        # Test with too many moving armies
        movement.moving_armies = 5
        self.assertFalse(movement.can_move())


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
        with patch("builtins.print"):
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
        with patch("builtins.print"):
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

        with patch("builtins.print"):
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
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = None

        result = self.turn_manager.is_turn_complete()

        self.assertTrue(result)

    def test_is_turn_complete_moving_phase_with_movement(self):
        """Test turn completion in moving phase with active movement."""
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = Mock()

        result = self.turn_manager.is_turn_complete()

        self.assertFalse(result)

    def test_is_turn_complete_other_phases(self):
        """Test turn completion in placement and attacking phases."""
        with patch("builtins.print"):
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
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.reinforcements_remaining = 2

        result = self.turn_manager.can_advance_phase()

        self.assertFalse(result)

    def test_can_advance_phase_placement_no_reinforcements(self):
        """Test phase advancement check in placement without reinforcements."""
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.reinforcements_remaining = 0

        result = self.turn_manager.can_advance_phase()

        self.assertTrue(result)

    def test_can_advance_phase_attacking(self):
        """Test phase advancement check in attacking phase."""
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.ATTACKING

        result = self.turn_manager.can_advance_phase()

        self.assertTrue(result)

    def test_can_advance_phase_moving_with_movement(self):
        """Test phase advancement check in moving with active movement."""
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = Mock()

        result = self.turn_manager.can_advance_phase()

        self.assertFalse(result)

    def test_can_advance_phase_moving_no_movement(self):
        """Test phase advancement check in moving without active movement."""
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.phase = TurnPhase.MOVING
            self.turn_manager.current_turn.current_movement = None

        result = self.turn_manager.can_advance_phase()

        self.assertTrue(result)

    def test_advance_turn_phase_success(self):
        """Test successful turn phase advancement."""
        with patch("builtins.print"):
            self.turn_manager.start_player_turn(1)
            self.turn_manager.current_turn.reinforcements_remaining = 0

        result = self.turn_manager.advance_turn_phase()

        self.assertTrue(result)
        self.assertEqual(self.turn_manager.current_turn.phase, TurnPhase.ATTACKING)

    def test_advance_turn_phase_no_turn(self):
        """Test turn phase advancement fails with no active turn."""
        result = self.turn_manager.advance_turn_phase()

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
