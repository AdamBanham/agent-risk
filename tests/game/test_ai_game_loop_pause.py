"""
Tests for pause functionality in AIGameLoop.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from risk.agents.ai_game_loop import AIGameLoop
from risk.state.game_state import GamePhase


class TestAIGameLoopPause(unittest.TestCase):
    """Test pause functionality in the AI-enhanced game loop."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock pygame to avoid initialization during tests
        self.pygame_mock = patch('pygame.init')
        self.pygame_mock.start()
        
        # Mock print to suppress pause messages during tests
        self.print_mock = patch('builtins.print')
        self.print_mock.start()
        
        # Create AI game loop for testing
        self.ai_game_loop = AIGameLoop(width=800, height=600, regions=3, 
                                      num_players=2, starting_armies=5)
        
        # Mock pygame display and components
        with patch('pygame.display.set_mode'), \
             patch('pygame.display.set_caption'), \
             patch('pygame.time.Clock'):
            self.ai_game_loop.screen = Mock()
            self.ai_game_loop.clock = Mock()
            self.ai_game_loop.running = True
    
    def tearDown(self):
        """Clean up test environment."""
        self.print_mock.stop()
        self.pygame_mock.stop()
    
    def test_pause_prevents_ai_turn_execution(self):
        """Test that paused state prevents AI turn execution."""
        # Set up mocks
        mock_agent_controller = Mock()
        mock_turn_manager = Mock()
        mock_current_turn = Mock()
        mock_current_turn.player_id = 0
        mock_player = Mock()
        mock_player.is_human = False
        
        # Configure mocks
        self.ai_game_loop.agent_controller = mock_agent_controller
        self.ai_game_loop.turn_manager = mock_turn_manager
        self.ai_game_loop.game_state = Mock()
        self.ai_game_loop.game_state.phase = GamePhase.PLAYER_TURN
        self.ai_game_loop.game_state.update_player_statistics = Mock()
        self.ai_game_loop.game_state.get_player.return_value = mock_player
        
        mock_turn_manager.get_current_turn.return_value = mock_current_turn
        
        # Set up AI state
        self.ai_game_loop.ai_turn_in_progress = False
        self.ai_game_loop.last_ai_action_time = 0.0
        self.ai_game_loop.ai_turn_delay = 0.1
        
        # Test unpaused behavior (should execute AI turn)
        self.ai_game_loop.paused = False
        with patch.object(self.ai_game_loop, '_execute_ai_turn') as mock_execute:
            self.ai_game_loop.update()
            mock_execute.assert_called_once_with(0)
        
        # Reset mock
        mock_execute.reset_mock()
        
        # Test paused behavior (should NOT execute AI turn)
        self.ai_game_loop.paused = True
        with patch.object(self.ai_game_loop, '_execute_ai_turn') as mock_execute:
            self.ai_game_loop.update()
            mock_execute.assert_not_called()
    
    def test_pause_inheritance_from_parent(self):
        """Test that AIGameLoop properly inherits pause behavior from GameLoop."""
        # Mock the parent update method
        with patch('risk.agents.simple.ai_game_loop.BaseGameLoop.update') as mock_parent_update:
            # Set paused state
            self.ai_game_loop.paused = True
            
            # Call update
            self.ai_game_loop.update()
            
            # Verify parent update was called (which respects pause state)
            mock_parent_update.assert_called_once()
    
    def test_ai_execution_resumes_after_unpause(self):
        """Test that AI execution resumes correctly after unpausing."""
        # Set up mocks
        mock_agent_controller = Mock()
        mock_turn_manager = Mock()
        mock_current_turn = Mock()
        mock_current_turn.player_id = 0
        mock_player = Mock()
        mock_player.is_human = False
        
        # Configure mocks
        self.ai_game_loop.agent_controller = mock_agent_controller
        self.ai_game_loop.turn_manager = mock_turn_manager
        self.ai_game_loop.game_state = Mock()
        self.ai_game_loop.game_state.phase = GamePhase.PLAYER_TURN
        self.ai_game_loop.game_state.update_player_statistics = Mock()
        self.ai_game_loop.game_state.get_player.return_value = mock_player
        
        mock_turn_manager.get_current_turn.return_value = mock_current_turn
        
        # Set up AI state
        self.ai_game_loop.ai_turn_in_progress = False
        self.ai_game_loop.last_ai_action_time = 0.0
        self.ai_game_loop.ai_turn_delay = 0.1
        
        with patch.object(self.ai_game_loop, '_execute_ai_turn') as mock_execute:
            # Start paused - should not execute
            self.ai_game_loop.paused = True
            self.ai_game_loop.update()
            mock_execute.assert_not_called()
            
            # Unpause - should execute
            self.ai_game_loop.paused = False
            self.ai_game_loop.update()
            mock_execute.assert_called_once_with(0)
    
    def test_ai_turn_delay_respected_when_not_paused(self):
        """Test that AI turn delay is still respected when not paused."""
        # Set up mocks
        mock_agent_controller = Mock()
        mock_turn_manager = Mock()
        mock_current_turn = Mock()
        mock_current_turn.player_id = 0
        mock_player = Mock()
        mock_player.is_human = False
        
        # Configure mocks
        self.ai_game_loop.agent_controller = mock_agent_controller
        self.ai_game_loop.turn_manager = mock_turn_manager
        self.ai_game_loop.game_state = Mock()
        self.ai_game_loop.game_state.phase = GamePhase.PLAYER_TURN
        self.ai_game_loop.game_state.update_player_statistics = Mock()
        self.ai_game_loop.game_state.get_player.return_value = mock_player
        
        mock_turn_manager.get_current_turn.return_value = mock_current_turn
        
        # Set up AI state with recent action time
        self.ai_game_loop.ai_turn_in_progress = False
        self.ai_game_loop.last_ai_action_time = time.time()  # Recent action
        self.ai_game_loop.ai_turn_delay = 10.0  # Long delay
        self.ai_game_loop.paused = False
        
        with patch.object(self.ai_game_loop, '_execute_ai_turn') as mock_execute:
            # Should not execute due to delay even when not paused
            self.ai_game_loop.update()
            mock_execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()