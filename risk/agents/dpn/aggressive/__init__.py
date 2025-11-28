"""
This module contains the logic for Data Petri Net (DPN) 
Aggressive Agent Implementation.
"""

from ...agent import BaseAgent
from risk.utils.logging import info

from .placement import PlacementPlanner
from .attack import AttackPlanner
from .movement import MovementPlanner

class DPNAggressiveAgent(BaseAgent):
    """
    A simple DPN agent that makes aggressive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id,
            "dpn-aggressive-agent-{}".format(player_id),
            attack_probability=attack_probability,
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} deciding placement...")

        planner = PlacementPlanner(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} deciding attacks...")

        planner = AttackPlanner(self.player_id, 10)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} deciding movement...")

        planner = MovementPlanner(self.player_id, 20)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events
