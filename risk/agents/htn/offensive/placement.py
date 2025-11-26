from risk.agents.plans import Planner, TroopPlacementStep, PlacementPlan
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug

from risk.agents.htn import gtpyhop as ghop
from ..bases import (
    include_commands,
    include_methods,
    Selector,
    HTNStateWithPlan,
    BuildStep,
    Computer,
    Filter,
)
import random
from dataclasses import dataclass, field
from typing import List, Collection


@dataclass
class PlacementState(HTNStateWithPlan):
    placements: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronts: List[mapping.SafeNode] = field(default_factory=list)
    terr: mapping.SafeNode = None
    actions: List[TroopPlacementStep] = field(default_factory=list)


def drop_placements(dom, arg, places):
    pass


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_aggressive_placement")

    include_commands()

    ## declare actions
    include_methods()

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "placing",
        drop_placements,
    )


def construct_planning_state(
    state: GameState, player: int, placements: int
) -> ghop.State:
    new_map = state.map.clone()
    safe_map = mapping.construct_safe_view(new_map, player)

    placement_state = PlacementState(
        player=player,
        placements=placements,
        map=new_map,
        safe_map=safe_map,
    )

    state = ghop.State(
        "placements",
        placing=placement_state,
    )

    return state


class PlacementPlanner(Planner):
    """
    Aggressive placement planner for troops in Risk.
    """

    def __init__(self, player_id: int, placements: int):
        super().__init__()
        self.player = player_id
        self.placements = placements

    def construct_plan(self, state: GameState) -> PlacementPlan:
        """Create a placement plan for the given player in the current state."""

        plan = PlacementPlan(self.placements)

        pstate = construct_planning_state(state, self.player, self.placements)
        construct_planning_domain(state)
        final_state = ghop.run_lazy_lookahead(
            pstate, [("placing", "placed", self.placements)]
        )
        actions = final_state.placing.actions
        debug(f"Generated actions for placement plan: {actions}")

        for action in actions:
            plan.add_step(action)

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG

    setLevel(DEBUG)

    ghop.verbose = 0
    placements = random.randint(1, 5)

    state = GameState.create_new_game(25, 2, 100)
    state.initialise()

    planner = PlacementPlanner(0, placements)
    plan = planner.construct_plan(state)

    print("Generated Placement Plan:", plan)
    assert (
        len(plan.steps) == placements
    ), "Number of placement steps should equal placements"
    for step in plan.steps:
        print(step)
