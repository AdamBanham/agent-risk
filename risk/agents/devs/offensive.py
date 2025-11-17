"""
This module contains the logic for Discrete EVent System simulator (DEVS)
Offensive Agent Implementation.
"""

from ..agent import BaseAgent

class DEVSOffensiveAgent(BaseAgent):
    """
    A simple BPMN agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "devs-offensive-agent-{}".format(player_id))