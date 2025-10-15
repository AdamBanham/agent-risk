"""
Extended game loop with AI agent integration.
Enhances the base GameLoop to support automatic AI turn execution.
"""

import time
from typing import Optional

from ...game.loop import GameLoop as BaseGameLoop
from ...state.game_state import GamePhase
from .random_agent import AgentController


class AIGameLoop(BaseGameLoop):
    """
    Extended game loop that supports AI agent turn execution. Automatically 
    executes turns for AI players while maintaining human interaction for 
    human players.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the AI-enabled game loop. Extends base GameLoop with agent 
        controller support.
        
        :param args: Arguments passed to base GameLoop
        :param kwargs: Keyword arguments passed to base GameLoop
        """
        super().__init__(*args, **kwargs)
        self.agent_controller: Optional[AgentController] = None
        self.ai_turn_delay = 1.0  # Seconds to wait between AI actions for visibility
        self.last_ai_action_time = 0.0
        self.ai_turn_in_progress = False
    
    def set_agent_controller(self, controller: AgentController) -> None:
        """
        Set the agent controller for managing AI players. Associates the 
        controller with this game loop for turn execution.
        
        :param controller: AgentController instance managing AI agents
        """
        self.agent_controller = controller
        print("AI agent controller registered with game loop")
    
    def update(self) -> None:
        """
        Enhanced update method that handles both human and AI player turns. 
        Automatically executes AI turns while preserving human interaction.
        Respects pause state from parent GameLoop.
        """
        # Call parent update method (which respects pause state)
        super().update()
        
        # Only execute AI logic when not paused
        if self.paused:
            return
        
        # Check if we have an active turn and agent controller
        if (self.agent_controller and self.turn_manager and 
            self.game_state.phase == GamePhase.PLAYER_TURN):
            
            current_turn = self.turn_manager.get_current_turn()
            if current_turn and not self.ai_turn_in_progress:
                
                current_player = self.game_state.get_player(current_turn.player_id)
                if current_player and not current_player.is_human:
                    
                    # Check if enough time has passed since last AI action
                    current_time = time.time()
                    if current_time - self.last_ai_action_time >= self.ai_turn_delay:
                        
                        # Execute AI turn
                        self.ai_turn_in_progress = True
                        self._execute_ai_turn(current_turn.player_id)
                        self.last_ai_action_time = current_time
                        self.ai_turn_in_progress = False
    
    def _execute_ai_turn(self, player_id: int) -> None:
        """
        Execute a complete AI turn for the specified player. Handles all 
        phases of the turn using the agent's decision-making.
        
        :param player_id: ID of the AI player whose turn to execute
        """
        if not self.agent_controller or not self.turn_manager:
            return
        
        agent = self.agent_controller.get_agent(player_id)
        if not agent:
            return
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn or current_turn.player_id != player_id:
            return
        
        print(f"\n=== {agent.name} executing turn ===")
        
        # Execute the agent's turn
        try:
            success = self.agent_controller.execute_agent_turn(
                self.game_state, self.turn_manager
            )
            
            if success:
                # Update game state after agent actions
                self.game_state.update_player_statistics()
                
                # Check for victory condition
                winner = self.game_state.check_victory_condition()
                if winner is not None:
                    winner_player = self.game_state.get_player(winner)
                    winner_name = winner_player.name if winner_player else f"Player {winner}"
                    print(f"\n🎉 Game Over! {winner_name} wins! 🎉")
                    self.game_state.phase = GamePhase.GAME_END
                    return
                
                # End the current turn and advance to next player
                if self.turn_manager.end_current_turn():
                    # Update UI to reflect new turn state
                    if self.renderer:
                        new_turn = self.turn_manager.get_current_turn()
                        if new_turn:
                            self.renderer.set_turn_state(new_turn)
                else:
                    # Game should end
                    print("No more active players - game ending")
                    self.game_state.phase = GamePhase.GAME_END
                
        except Exception as e:
            print(f"Error executing AI turn for player {player_id}: {e}")
            # Continue game even if AI turn fails
            self.ai_turn_in_progress = False
    
    def is_current_player_ai(self) -> bool:
        """
        Check if the current active player is controlled by an AI agent. Used 
        to determine if automatic turn execution should occur.
        
        :returns: True if current player is AI, False if human or no current 
                 player
        """
        if not self.agent_controller or not self.turn_manager:
            return False
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn:
            return False
        
        return self.agent_controller.is_agent_player(current_turn.player_id)
    
    def get_current_player_info(self) -> str:
        """
        Get information about the current active player. Provides details 
        about whether the player is human or AI controlled.
        
        :returns: String describing the current player and their control type
        """
        if not self.turn_manager:
            return "No active turn"
        
        current_turn = self.turn_manager.get_current_turn()
        if not current_turn:
            return "No active turn"
        
        player = self.game_state.get_player(current_turn.player_id)
        if not player:
            return f"Unknown player {current_turn.player_id}"
        
        player_type = "AI" if not player.is_human else "Human"
        return f"{player.name} ({player_type})"
    
    def set_ai_turn_delay(self, delay: float) -> None:
        """
        Set the delay between AI actions for better visibility. Allows 
        adjustment of AI turn speed for demonstration purposes.
        
        :param delay: Delay in seconds between AI actions (minimum 0.1)
        """
        self.ai_turn_delay = max(0.1, delay)
        print(f"AI turn delay set to {self.ai_turn_delay:.1f} seconds")


def create_ai_game(regions: int = 15, num_players: int = 3, starting_armies: int = 20,
                   ai_player_ids: list = None, attack_probability: float = 0.5,
                   ai_delay: float = 1.0) -> AIGameLoop:
    """
    Factory function to create a complete AI-enabled game setup. Creates game 
    loop, agent controller, and configures AI players.
    
    :param regions: Number of territories to generate (g parameter)
    :param num_players: Number of players in the simulation (p parameter)
    :param starting_armies: Starting army size per player (s parameter)
    :param ai_player_ids: List of player IDs to be controlled by AI agents
    :param attack_probability: Probability that AI agents will attack when 
                              opportunities arise
    :param ai_delay: Delay in seconds between AI actions for visibility
    :returns: Configured AIGameLoop ready to run with AI agents
    """
    if ai_player_ids is None:
        ai_player_ids = list(range(1, num_players))  # Default: all except player 0
    
    # Create the enhanced game loop
    game_loop = AIGameLoop(
        width=1800,
        height=1028,
        regions=regions,
        num_players=num_players,
        starting_armies=starting_armies
    )
    
    # Set up AI agents if specified
    if ai_player_ids:
        from .random_agent import create_random_agents
        
        agent_controller = create_random_agents(
            game_loop.game_state,
            ai_player_ids,
            attack_probability=attack_probability
        )
        
        game_loop.set_agent_controller(agent_controller)
        game_loop.set_ai_turn_delay(ai_delay)
    
    return game_loop