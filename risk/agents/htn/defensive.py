"""
This module contains the logic for Hierarchical Task Network (HTN) 
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class HTNDefensiveAgent(BaseAgent):
    """
    A simple HTN agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "HTN-Defensive-Agent-{}".format(player_id))