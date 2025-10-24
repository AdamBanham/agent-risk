"""
This module contains the logic for Behaviour Tree (BT)
Offensive Agent Implementation.
"""

from ..agent import BaseAgent

class BTOffensiveAgent(BaseAgent):
    """
    A simple BT agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "BT-Offensive-Agent-{}".format(player_id))