"""
This module contains the logic for Data Petri Net (DPN) 
Offensive Agent Implementation.
"""

from ..agent import BaseAgent

class DPNOffensiveAgent(BaseAgent):
    """
    A simple DPN agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "DPN-Offensive-Agent-{}".format(player_id))
