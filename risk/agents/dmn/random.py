"""
This module contains the logic for Decision Model and Notation (DMN) 
Random Agent Implementation.
"""

import random
from typing import List

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence, Movement
from ...utils.movement import find_safe_frontline_territories
from ...utils.movement import find_connected_frontline_territories


from ..agent import BaseAgent
from risk.state.plan import Goal
from risk.state.event_stack import (
    TroopPlacementEvent,
    AttackOnTerritoryEvent,
    MovementOfTroopsEvent,
    Event
)

class DMNRandomAgent(BaseAgent):
    """
    A simple DMN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "DMN-Random-Agent-{}".format(player_id))