from risk.agents.plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug

from risk.agents.htn import gtpyhop as ghop
from ..bases import Selector, HTNStateWithPlan, BuildStep, Computer, Filter

import random
from dataclasses import dataclass, field
from typing import List, Collection

@dataclass
class MovementState(HTNStateWithPlan):
    placements: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronts: List[mapping.SafeNode] = field(default_factory=list)
    terr: mapping.SafeNode = None
    actions: List[MovementStep] = field(default_factory=list)

def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_defensive_movement")

    ## declare actions
    ghop.declare_actions(
    )

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "moving",
        ...,
    )


def construct_planning_state(state: GameState, player: int, placements: int):
    new_map = state.map.clone()
    safe_map = mapping.construct_safe_view(new_map, player)

    placement_state = MovementState(
        player=player,
        placements=placements,
        map=new_map,
        safe_map=safe_map,
    )

    state = ghop.State(
        "moves",
        moving=placement_state,
    )

    return state


class MovementPlanner(Planner):
    """A planner for placing troops defensively in Risk."""

    def __init__(self, player_id: int):
        super().__init__()
        self.player = player_id

    def construct_plan(self, state: GameState) -> MovementPlan:
        """Create a placement plan for the given player in the current state."""

        plan = MovementPlan()

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

    planner = MovementPlanner(0)
    plan = planner.construct_plan(state)

    print("Generated Movement Plan:", plan)

    for step in plan.steps:
        print(step)