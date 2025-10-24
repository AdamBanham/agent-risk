"""
This module contains the logic for Monte Carlo Tree Search (MCTS) 
Random Agent Implementation.
"""

from ..agent import BaseAgent

class MCSTRandomAgent(BaseAgent):
    """
    A simple MCTS agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "MCTS-Random-Agent-{}".format(player_id))