from risk.agents.plans import Planner, TroopPlacementStep, PlacementPlan
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug

from risk.agents.htn import gtpyhop as ghop
from ..bases import (
    include_commands, include_methods,
    Selector, HTNStateWithPlan, BuildStep, Computer, Filter
)
import random
from dataclasses import dataclass, field
from typing import List, Collection


@dataclass
class DefensivePlacementState(HTNStateWithPlan):
    placements: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronts: List[mapping.SafeNode] = field(default_factory=list)
    terr: mapping.SafeNode = None
    actions: List[TroopPlacementStep] = field(default_factory=list)


def construct_step(state: DefensivePlacementState) -> TroopPlacementStep:
    return TroopPlacementStep(
        territory=state.terr.id,
        troops=1,
    )


def update_placed(state: DefensivePlacementState):
    return state.placed + 1


def filter_fronts(
    state: DefensivePlacementState, collection: Collection[mapping.SafeNode]
) -> Collection[mapping.SafeNode]:

    n_most = random.randint(1, len(collection))
    top_most = sorted(
        collection,
        key=lambda t: state.map.get_node(t.id).value,
        reverse=True,
    )[: int(n_most)]

    return top_most


## methods
def drop_placements(dom, arg, places):
    state: DefensivePlacementState = dom.placing
    if len(state.safe_map.frontline_nodes) == 0:
        return False
    elif len(state.fronts) == 0:
        return [
            ("filter_fronts", state.safe_map.frontline_nodes),
            ("placing", arg, places),
        ]
    elif state.placed < state.placements:
        return [
            ("select_terr", state.fronts),
            ("build_step",),
            ("compute_placed",),
            ("placing", arg, places),
        ]
    elif state.placed == state.placements:
        return []
    else:
        return False


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_defensive_placement")

    include_commands()

    ## declare actions
    include_methods(
        Selector(to_key="terr", namespace="placing"),
        BuildStep("actions", "placing", construct_step),
        Computer("placed", "placing", update_placed),
        Filter("fronts", "placing", filter_fronts),
    )

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "placing",
        drop_placements,
    )


def construct_planning_state(state: GameState, player: int, placements: int):
    new_map = state.map.clone()
    safe_map = mapping.construct_safe_view(new_map, player)

    placement_state = DefensivePlacementState(
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
    """A planner for placing troops defensively in Risk."""

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

    terrs = mapping.construct_safe_view(state.map, 0).frontline_nodes
    terr = random.choice(terrs)
    terr = state.get_territory(terr.id)
    terr.armies += 150
    info(
        f"Modified territory to have highest armies: {terr.id} with {terr.armies} armies, owned by player {terr.owner}"
    )
    state.update_player_statistics()

    planner = PlacementPlanner(0, placements)
    plan = planner.construct_plan(state)

    print("Generated Placement Plan:", plan)
    assert (
        len(plan.steps) == placements
    ), "Number of placement steps should equal placements"
    for step in plan.steps:
        print(step)

