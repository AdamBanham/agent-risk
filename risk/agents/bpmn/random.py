"""
This module contains the logic for Business Process Model and Notation (BPMN) 
Random Agent Implementation.
"""

from ..agent import BaseAgent

class BPMNRandomAgent(BaseAgent):
    """
    A simple BPMN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "BPMN-Random-Agent-{}".format(player_id))