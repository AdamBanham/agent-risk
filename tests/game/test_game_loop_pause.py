"""
Tests for pause/unpause functionality in GameLoop.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pygame
from risk.game.loop import GameLoop


class TestGameLoopPause(unittest.TestCase):
    """Test pause functionality in the game loop."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock pygame to avoid initialization during tests
        self.pygame_mock = patch('pygame.init')
        self.pygame_mock.start()
        
        # Create minimal game loop for testing
        self.game_loop = GameLoop(width=800, height=600, regions=3, 
                                 num_players=2, starting_armies=5)
        
        # Mock pygame display
        with patch('pygame.display.set_mode'), \
             patch('pygame.display.set_caption'), \
             patch('pygame.time.Clock'):
            self.game_loop.screen = Mock()
            self.game_loop.clock = Mock()
            self.game_loop.running = True
    
    def tearDown(self):
        """Clean up test environment."""
        self.pygame_mock.stop()
    
    def test_initial_pause_state(self):
        """Test that game starts unpaused."""
        self.assertFalse(self.game_loop.paused)
    
    def test_toggle_pause_first_time(self):
        """Test toggling pause from unpaused to paused state."""
        # Initially unpaused
        self.assertFalse(self.game_loop.paused)
        
        # Mock pygame display for caption update
        with patch('pygame.display.set_caption') as mock_caption:
            # Toggle pause
            self.game_loop._handle_toggle_pause(None)
            
            # Should now be paused
            self.assertTrue(self.game_loop.paused)
            
            # Should update window caption
            mock_caption.assert_called_with("Agent Risk - Dynamic Board Simulation [PAUSED]")
    
    def test_toggle_pause_second_time(self):
        """Test toggling pause from paused back to unpaused state."""
        # Start with paused state
        self.game_loop.paused = True
        
        # Mock pygame display for caption update
        with patch('pygame.display.set_caption') as mock_caption:
            # Toggle pause again
            self.game_loop._handle_toggle_pause(None)
            
            # Should now be unpaused
            self.assertFalse(self.game_loop.paused)
            
            # Should update window caption
            mock_caption.assert_called_with("Agent Risk - Dynamic Board Simulation")
    
    def test_update_respects_pause_state(self):
        """Test that update only runs when not paused."""
        # Mock the game state update method
        self.game_loop.game_state = Mock()
        self.game_loop.game_state.update_player_statistics = Mock()
        
        # Test unpaused update
        self.game_loop.paused = False
        self.game_loop.update()
        self.game_loop.game_state.update_player_statistics.assert_called_once()
        
        # Reset mock
        self.game_loop.game_state.update_player_statistics.reset_mock()
        
        # Test paused update
        self.game_loop.paused = True
        self.game_loop.update()
        self.game_loop.game_state.update_player_statistics.assert_not_called()
    
    @patch('pygame.font.Font')
    @patch('pygame.Surface')
    def test_pause_overlay_rendering(self, mock_surface, mock_font):
        """Test that pause overlay is rendered when paused."""
        # Set up mocks
        self.game_loop.screen = Mock()
        self.game_loop.width = 800
        self.game_loop.height = 600
        
        # Mock font rendering
        mock_font_instance = Mock()
        mock_font.return_value = mock_font_instance
        mock_text_surface = Mock()
        mock_text_surface.get_rect.return_value = Mock()
        mock_font_instance.render.return_value = mock_text_surface
        
        # Mock surface creation
        mock_overlay = Mock()
        mock_surface.return_value = mock_overlay
        
        # Test pause overlay drawing
        self.game_loop._draw_pause_overlay()
        
        # Verify overlay surface was created and configured
        mock_surface.assert_called_with((800, 600))
        mock_overlay.set_alpha.assert_called_with(128)
        mock_overlay.fill.assert_called_with((0, 0, 0))
        self.game_loop.screen.blit.assert_called()
    
    def test_render_includes_pause_overlay_when_paused(self):
        """Test that render method includes pause overlay when paused."""
        # Set up mocks
        self.game_loop.renderer = Mock()
        self.game_loop.screen = Mock()
        
        with patch.object(self.game_loop, '_draw_pause_overlay') as mock_overlay, \
             patch('pygame.display.flip'):
            
            # Test rendering when not paused
            self.game_loop.paused = False
            self.game_loop.render()
            mock_overlay.assert_not_called()
            
            # Test rendering when paused
            self.game_loop.paused = True
            self.game_loop.render()
            mock_overlay.assert_called_once()
    
    def test_multiple_pause_toggles(self):
        """Test multiple pause/unpause cycles."""
        initial_state = self.game_loop.paused
        
        with patch('pygame.display.set_caption'):
            # Toggle multiple times
            for i in range(5):
                self.game_loop._handle_toggle_pause(None)
                expected_state = not initial_state if i % 2 == 0 else initial_state
                self.assertEqual(self.game_loop.paused, expected_state)


if __name__ == '__main__':
    unittest.main()