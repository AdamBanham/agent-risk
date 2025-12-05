"""
This module contains the logic for Behaviour Tree (BT)
Random Agent Implementation.
"""

from risk.agents import BaseAgent
from risk.utils.logging import info
from risk.utils import map as mapping
from risk.utils.movement import find_movement_sequence
from ...plans import RouteMovementStep, MovementStep

from .placement import PlacementPlanner
from .attack import AttackPlanner
from .movement import MovementPlanner


class BTRandomAgent(BaseAgent):
    """
    A simple BT agent that makes random decisions during placement, attack,
    and defense phases.
    """

    def __init__(self, player_id: int, attack_probability: float):
        super().__init__(
            player_id, "bt-random-agent-{}".format(player_id), attack_probability
        )

    def decide_placement(self, game_state, goal):
        info(f"{self.name} planning for placement...")

        planner = PlacementPlanner(
            self.player_id,
            game_state.placements_left,
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} planning for attacking...")

        planner = AttackPlanner(
            self.player_id,
            10,
            self.attack_probability
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} planning for movement...")

        planner = MovementPlanner(
            self.player_id,
            1,
        )
        plan = planner.construct_plan(game_state)

        events = []
        while not plan.is_done():
            step: MovementStep = plan.pop_step()

            route = find_movement_sequence(
                game_state.get_territory(step.source),
                game_state.get_territory(step.destination),
                step.troops,
            )

            step = RouteMovementStep(
                [MovementStep(r.src.id, r.tgt.id, r.amount) for r in route], step.troops
            )

            events.extend(step.execute(game_state))

        return events
