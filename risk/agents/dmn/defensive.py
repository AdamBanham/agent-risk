"""
This module contains the logic for Decision Model and Notation (DMN)
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class DMNDefensiveAgent(BaseAgent):
    """
    A simple DMN agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "DMN-Defensive-Agent-{}".format(player_id))