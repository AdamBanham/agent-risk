"""
This module contains the logic for Behaviour Tree (BT)
Random Agent Implementation.
"""

from risk.agents import BaseAgent
from risk.utils.logging import info
from risk.utils import map as mapping
from risk.utils.movement import find_movement_sequence
from ...plans import RouteMovementStep, MovementStep

from .placement import RandomPlacements
from .attack import RandomAttacks
from .movement import RandomMovements


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

        terrs = game_state.get_territories_owned_by(self.player_id)

        planner = RandomPlacements(
            self.player_id,
            game_state.placements_left,
            [t.id for t in terrs],
            game_state,
        )
        planner.construct_plan()
        plan = planner.plan

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_attack(self, game_state, goal):
        info(f"{self.name} planning for attacking...")

        map = game_state.map
        safe_map = mapping.construct_safe_view(map, self.player_id)

        planner = RandomAttacks(
            self.player_id,
            10,
            [
                t.id
                for t in safe_map.frontline_nodes
                if mapping.get_value(map, t.id) > 1
            ],
            game_state,
            self.attack_probability,
        )
        planner.construct_plan()
        plan = planner.plan

        events = []
        while not plan.is_done():
            step = plan.pop_step()
            events.extend(step.execute(game_state))

        return events

    def decide_movement(self, game_state, goal):
        info(f"{self.name} planning for movement...")

        map = game_state.map
        network_map = mapping.construct_network_view(map, self.player_id)

        planner = RandomMovements(
            self.player_id,
            1,
            [t.id for t in network_map.nodes if t.safe],
            map,
            network_map,
        )
        plan = planner.construct_plan()

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
