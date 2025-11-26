"""
This module contains the logic for Monte Carlo Tree Search (MCTS)
Offensive Agent Implementation.
"""
from risk.utils.logging import info
from ...agent import BaseAgent


class MCTSAggressiveAgent(BaseAgent):
    """
    A simple MCTS agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id,
            "mcts-aggressive-agent-{}".format(player_id),
            attack_probability=attack_probability,
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} deciding placement...")
        return super().decide_placement(game_state, goal)

    def decide_attack(self, game_state, goal):
        info(f"{self.name} deciding attacks...")
        return super().decide_attack(game_state, goal)

    def decide_movement(self, game_state, goal):
        info(f"{self.name} deciding movement...")
        return super().decide_movement(game_state, goal)
