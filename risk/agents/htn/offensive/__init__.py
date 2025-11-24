"""
This module contains the logic for Hierarchical Task Network (HTN) 
Offensive Agent Implementation.
"""

from ...agent import BaseAgent

class HTNOffensiveAgent(BaseAgent):
    """
    A simple HTN agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "HTN-Offensive-Agent-{}".format(player_id))