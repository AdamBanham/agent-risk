"""
This module contains the logic for Monte Carlo Tree Search (MCTS) 
Offensive Agent Implementation.
"""

from ..agent import BaseAgent

class MCTSOffensiveAgent(BaseAgent):
    """
    A simple MCTS agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "MCTS-Offensive-Agent-{}".format(player_id))