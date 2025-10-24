"""
This module contains the logic for Business Process Model and Notation (BPMN)
Defensive Agent Implementation.
"""

from ..agent import BaseAgent

class BPMNDefensiveAgent(BaseAgent):
    """
    A simple BPMN agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "BPMN-Defensive-Agent-{}".format(player_id))