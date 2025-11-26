"""
This module contains the logic for Hierarchical Task Network (HTN)
Offensive Agent Implementation.
"""

from risk.utils.logging import info
from ...agent import BaseAgent

from .placement import PlacementPlanner
from .attack import AttackPlanner
from .movement import MovementPlanner


class HTNAggressiveAgent(BaseAgent):
    """
    A simple HTN agent that makes offensive decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float = 0.5):
        super().__init__(
            player_id,
            "htn-offensive-agent-{}".format(player_id),
            attack_probability=attack_probability,
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} deciding placements...")
        planner = PlacementPlanner(self.player_id, game_state.placements_left)
        plan = planner.construct_plan(game_state)

        events = []
        assert (
            len(plan.steps) == 1
        ), "Placement plan steps are not singular."
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} deciding attacks...")
        planner = AttackPlanner(self.player_id, max_attacks=10)
        plan = planner.construct_plan(game_state)

        events = []
        assert len(plan.steps) <= 10, "Attack plan steps has too many attacks."
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} deciding movements...")

        planner = MovementPlanner(
            self.player_id,
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))
        return events
