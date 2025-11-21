"""
This module contains the logic for Behaviour Tree (BT)
aggressive agent implementation.
"""

from ...agent import BaseAgent
from .placement import PlacementPlanner
from .attack import AttackPlanner
from .movement import MovementPlanner

from risk.utils.logging import info


class BTAggresiveAgent(BaseAgent):
    """
    A simple BT agent that makes aggresive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id, "bt-aggressive-agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} deciding placements...")

        planner = PlacementPlanner(
            self.player_id, placements=game_state.placements_left
        )
        plan = planner.construct_plan(game_state)

        events = []

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} deciding attacks...")

        planner = AttackPlanner(self.player_id, 10, self.attack_probability)
        plan = planner.construct_plan(game_state)

        events = []

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} deciding movement...")

        planner = MovementPlanner(self.player_id)
        plan = planner.construct_plan(game_state)

        events = []

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events
