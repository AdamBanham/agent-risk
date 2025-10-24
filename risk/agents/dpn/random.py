"""
This module contains the logic for Data Petri Net (DPN) 
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

class DPNRandomAgent(BaseAgent):
    """
    A simple DPN agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id, "DPN-Random-Agent-{}".format(player_id))