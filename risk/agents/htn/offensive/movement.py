from risk.agents.plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.movement import find_movement_sequence
from risk.utils.logging import debug

from risk.agents.htn import gtpyhop as ghop
from ..bases import (
    include_commands, include_methods,
    Selector, HTNStateWithPlan, BuildStep, Computer, Filter, Reseter
)
import random
from dataclasses import dataclass, field
from typing import List, Collection
from copy import deepcopy


@dataclass
class MovementState(HTNStateWithPlan):
    balanced: int = 0
    map: mapping.Graph = None
    network_map: mapping.NetworkGraph = None
    networks: set[int] = field(default_factory=set)
    network: int = None
    view: mapping.NetworkGraph = None
    fronts: List[mapping.NetworkNode] = None
    free: List[mapping.NetworkNode] = field(default_factory=list)
    tgt: mapping.NetworkNode = None
    src: mapping.NetworkNode = None
    amount: int = 0
    target: int = -1
    actions: List[MovementStep] = field(default_factory=list)


def decide_moves(dom, arg, places):
    pass


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_aggressive_movement")

    include_commands()

    ## declare actions
    include_methods()

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "moving",
        decide_moves,
    )


def construct_planning_state(state: GameState, player: int):
    new_map = mapping.construct_graph(state)
    safe_map = mapping.construct_network_view(new_map, player)

    data_state = MovementState(
        player=player,
        map=new_map,
        network_map=safe_map,
        networks=set(safe_map.networks),
    )

    state = ghop.State(
        "moving",
        moving=data_state,
    )

    return state


class MovementPlanner(Planner):
    """
    Aggressive attack planner for troops in Risk.
    """

    def __init__(self, player_id: int,):
        super().__init__()
        self.player = player_id

    def construct_plan(self, state: GameState) -> MovementPlan:
        """Create a movement plan for the given player in the current state."""


        pstate = construct_planning_state(state, self.player)
        construct_planning_domain(state)
        final_state = ghop.run_lazy_lookahead(
            pstate, [("moving", "balanced", len(pstate.moving.networks))]
        )
        actions = final_state.moving.actions
        debug(f"Generated actions for movement plan: {actions}")

        plan = MovementPlan(len(actions))
        for action in reversed(actions):
            plan.add_step(action)

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG

    setLevel(DEBUG)

    ghop.verbose = 0
    max_attacks = random.randint(1, 5)

    state = GameState.create_new_game(25, 2, 100)
    state.initialise()

    planner = AttackPlanner(0, max_attacks)
    plan = planner.construct_plan(state)

    print("Generated Attack Plan:", plan)
    for step in plan.steps:
        print(step)
