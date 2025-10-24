"""
This module contains the logic for Business Process Model and Notation (BPMN)
Offensive Agent Implementation.
"""

from ..agent import BaseAgent

class BPMNOffensiveAgent(BaseAgent):
    """
    A simple BPMN agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "BPMN-Offensive-Agent-{}".format(player_id))