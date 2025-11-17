"""
This module contains the logic for Discrete EVent System simulator (DEVS)
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class DEVSDefensiveAgent(BaseAgent):
    """
    A simple DEVS agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "devs-defensive-agent-{}".format(player_id))