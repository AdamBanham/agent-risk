from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState
from risk.utils.logging import debug, info
from risk.utils import map as mapping

import random
from typing import Set

from xdevs.models import Coupled
from xdevs.sim import Coordinator
from ..base import Selector, Reworker, Builder, Filter


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
    

class AttackFilter(Filter[Set[int], Set[int]]):
    """
    Filters fronts down to the a singleton set of containing the
    territory with the most attack potential.
    """

    def __init__(self, map: mapping.Graph, player: int):
        super().__init__("attack-filter")
        self._map = map 
        self._player = player

    def sort_key(self, item) -> float:
        total = 0
        armies = self._map.get_node(item).value
        for neighbor in self._map.get_adjacent_nodes(item):
            if neighbor.owner != self._player:
                total += armies / neighbor.value
        return total

    def filter(self, item):
        ret = list(item)
        ret = sorted(
            item, key=self.sort_key, reverse=True
        )
        return set(ret[:1])

class PlacementModel(Coupled):
    """
    A coupled model that constructs placements.
    """

    def __init__(self, player: int, map: mapping.Graph, placements: int):
        super().__init__("AggressivePlacementModel")

        self.placements = placements

        safe_map = mapping.construct_safe_view(map, player)
        fronts = {node.id for node in safe_map.frontline_nodes}

        self.selector = Selector("selector")
        self.filter = AttackFilter(map, player)
        self.builder = PlacementBuilder("builder")
        self.reworker = Reworker[TroopPlacementStep](
            "reworker", fronts, reworks=placements
        )

        self.add_component(self.filter)
        self.add_component(self.selector)
        self.add_component(self.builder)
        self.add_component(self.reworker)

        self.add_coupling(self.reworker.o_request, self.filter.i_filter)
        self.add_coupling(self.filter.o_filtered, self.selector.i_terrs)
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
    An aggressive placement planner.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, game_state: GameState) -> PlacementPlan:
        plan = PlacementPlan(self.placements)

        model = PlacementModel(self.player, game_state.map.clone(), self.placements)
        
        for action in model.start_planning():
            plan.add_step(action)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(20, 2, 50)
    state.initialise()
    state.update_player_statistics()

    planner = PlacementPlanner(0, 2)
    plan = planner.construct_plan(state)

    info("Constructed Plan: {}".format(plan))
    assert len(plan.steps) == 2, "Expected 2 placement steps in the plan."
    terr = None
    for step in plan.steps:
        info(" - Step: {}".format(step))
        if terr is None:
            terr = step.territory
        else:
            assert terr == step.territory, "Expected the same territory for placements"
