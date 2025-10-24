"""
This module contains the logic for Behaviour Tree (BT) 
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class BTDefensiveAgent(BaseAgent):
    """
    A simple BT agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "BT-Defensive-Agent-{}".format(player_id))