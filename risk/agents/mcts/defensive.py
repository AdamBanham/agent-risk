"""
This module contains the logic for Monte Carlo Tree Search (MCTS) 
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class MCTSDefensiveAgent(BaseAgent):
    """
    A simple MCTS agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "MCTS-Defensive-Agent-{}".format(player_id))