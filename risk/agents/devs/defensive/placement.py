from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState
from risk.utils.logging import info
from risk.utils import map as mapping

import random

from xdevs.models import Coupled
from xdevs.sim import Coordinator
from ..base import Selector, Reworker, Builder


class PlacementBuilder(Builder[TroopPlacementStep]):
    """
    An atomic model that waits for a territory and then
    builds a TroopPlacementStep using it.

    .. ports ::
        :port i_terr: int
        :port o_step: TroopPlacementStep
    """

    def __init__(self, name):
        super().__init__(
            name,
            {
                "terr": int,
            },
        )

    def build(self, inputs):
        return TroopPlacementStep(territory=inputs["terr"], troops=1)


class PlacementModel(Coupled):
    """
    A coupled model that constructs placements.
    """

    def __init__(self, player: int, map: mapping.Graph, placements: int):
        super().__init__("DefensivePlacementModel")

        self.placements = placements

        safe_map = mapping.construct_safe_view(map, player)

        n_most = random.randint(1, len(safe_map.frontline_nodes))
        top_most = sorted(
            safe_map.frontline_nodes,
            key=lambda t: map.get_node(t.id).value,
            reverse=True,
        )[: int(n_most)]

        fronts = {node.id for node in top_most}

        self.selector = Selector("selector")
        self.builder = PlacementBuilder("builder")
        self.reworker = Reworker[TroopPlacementStep](
            "reworker", fronts, reworks=placements
        )

        self.add_component(self.selector)
        self.add_component(self.builder)
        self.add_component(self.reworker)

        self.add_coupling(self.reworker.o_request, self.selector.i_terrs)
        self.add_coupling(self.selector.o_terr, self.builder.i_terr)
        self.add_coupling(self.builder.o_step, self.reworker.i_action)

    def initialize(self):
        super().initialize()

    def start_planning(self):
        coordinator = Coordinator(self)
        coordinator.initialize()
        coordinator.simulate()
        done_steps = self.reworker.get_actions()
        return done_steps


class PlacementPlanner(Planner):
    """
    A defensive placement planner.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, game_state: GameState) -> PlacementPlan:
        plan = PlacementPlan(self.placements)

        model = PlacementModel(
            self.player,
            game_state.map.clone(),
            self.placements,
        )

        for step in model.start_planning():
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)


    for _ in range(10):
        state = GameState.create_new_game(20, 2, 50)
        state.initialise()
        state.update_player_statistics()

        pick = random.randint(1, 5)
        planner = PlacementPlanner(0, pick)
        plan = planner.construct_plan(state)

        info("Constructed Plan: {}".format(plan))
        assert len(plan.steps) == pick, "Expected 2 placement steps in the plan."
        for step in plan.steps:
            info(" - Step: {}".format(step))
