"""
This module contains the logic for Discrete EVent System simulator (DEVS)
Defensive Agent Implementation.
"""

from ...agent import BaseAgent
from risk.utils.logging import info

from .placement import PlacementPlanner
from .attack import AttackPlanner
from .movement import MovementPlanner


class DEVSDefensiveAgent(BaseAgent):
    """
    A simple DEVS agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.3):
        super().__init__(player_id, "devs-defensive-agent-{}".format(player_id))

    def decide_placement(self, game_state, goal):
        info(f"{self.name} - planning for placement")
        planner = PlacementPlanner(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} - planning for attack")
        planner = AttackPlanner(self.player_id, 10)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} - planning for movement")
        planner = MovementPlanner(self.player_id)
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events
