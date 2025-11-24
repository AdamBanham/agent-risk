"""
This module contains the logic for Hierarchical Task Network (HTN)
Defensive Agent Implementation.
"""

from ...agent import BaseAgent

from .placement import PlacementPlanner
from risk.utils.logging import info


class HTNDefensiveAgent(BaseAgent):
    """
    A HTN agent that makes defensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(player_id, "htn-defensive-agent-{}".format(player_id), attack_probability=attack_probability)

    def decide_placement(self, game_state, goal):
        info(f"{self.name} is deciding placements...")

        planner = PlacementPlanner(
            self.player_id, game_state.placements_left
        )
        plan = planner.construct_plan(game_state)

        events = []
        assert len(plan.steps) == game_state.placements_left, \
            "Placement plan steps do not match placements left."
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} is deciding attacks...")
        return super().decide_attack(game_state, goal)

    def decide_movement(self, game_state, goal):
        info(f"{self.name} is deciding movements...")
        return super().decide_movement(game_state, goal)
