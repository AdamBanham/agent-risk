"""
Simple random AI agent for the Risk simulation.
Makes aggressive decisions for placement, attacking, and movement phases.
"""

import random
from typing import List

from ...state.game_state import GameState
from ...utils.movement import find_movement_sequence, Movement
from ...utils.movement import find_safe_frontline_territories
from ...utils.movement import find_connected_frontline_territories
from risk.utils.logging import debug, info


from ..agent import BaseAgent
from risk.state.plan import Goal
from risk.state.event_stack import (
    TroopPlacementEvent,
    AttackOnTerritoryEvent,
    MovementOfTroopsEvent,
    Event,
)


class AggressiveAgent(BaseAgent):
    """
    A simple aggressive AI agent that makes decisions for placement, attacking,
    and movement phases in the Risk simulation.

    :param player_id: ID of the player this agent controls
    :param attack_probability: Unused parameter for compatibility
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "simple-aggressive-agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state: GameState, goal: Goal) -> List[Event]:

        _, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )

        n_most = random.uniform(1, len(frontlines))
        top_most = sorted(frontlines, key=lambda t: t.armies, reverse=True)[
            : int(n_most)
        ]
        events = []
        for i in range(game_state.placements_left):
            if top_most:
                selected_territory = top_most[i % n_most]
                event = TroopPlacementEvent(
                    turn=game_state.total_turns,
                    player=self.player_id,
                    territory=selected_territory.id,
                    num_troops=1,
                )
                events.append(event)

        return events

    def decide_attack(self, game_state: GameState, goal: Goal) -> List[Event]:

        events = []

        return events

    def decide_movement(self, game_state: GameState, goal: Goal) -> List[Event]:

        events = []

        return events
