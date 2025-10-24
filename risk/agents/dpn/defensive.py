"""
This module contains the logic for Data Petri Net (DPN) 
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class DPNDefensiveAgent(BaseAgent):
    """
    A simple DPN agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "DPN-Defensive-Agent-{}".format(player_id))