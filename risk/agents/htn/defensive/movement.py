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


def compute_view(state: MovementState):
    return state.network_map.view(state.network)


def compute_target(state: MovementState):
    view = state.view
    armies = sum(state.map.get_node(n.id).value for n in state.view.nodes)
    safes = [n for n in state.view.nodes if n.safe]
    movable = armies - len(safes) 
    fronts = len(view.frontlines_in_network(state.network))
    target = (movable // fronts) if fronts > 0 else 0
    debug(f"Computing target for network {state.network} with total armies {armies} and view size {view.size}...")
    return target


def compute_fronts(state: MovementState):
    return [
        n
        for n in state.view.nodes 
        if not n.safe and state.map.get_node(n.id).value < state.target
    ]


def compute_free(state: MovementState):
    ret = []
    for n in state.view.frontlines_in_network(state.network):
        if state.map.get_node(n.id).value > state.target:
            ret.append(n)

    return ret + [
        n
        for n in state.view.nodes
        if n.safe and state.map.get_node(n.id).value > 1
    ]

def compute_amount(state: MovementState):

    missing_troops = state.target - state.map.get_node(state.tgt.id).value
    what_src_can_give = state.map.get_node(state.src.id).value - 1

    selected_amount = min(
        what_src_can_give,
        missing_troops,
    )
    assert selected_amount >= 1, f"Computed amount must be at least 1, got {selected_amount}, {what_src_can_give}, {missing_troops}"
    return selected_amount

def build_step(state: MovementState) -> MovementStep:
    return MovementStep(
        source=state.src.id,
        destination=state.tgt.id,
        troops=state.amount,
    )

# actions 
def update_map(state: MovementState):
    step = state.actions[-1]
    map = deepcopy(state.map)
    map.get_node(step.source).value -= step.troops
    map.get_node(step.destination).value += step.troops
    return map

def check_for_free(dom):
    debug("Checking for free troops to move...")
    if len(dom.moving.free) == 0:
        return []
    else:
        return [
            ("select_src", "free"),
            ("select_tgt", "fronts"),
            ("compute_amount",),
            ("build_step",),
            ("compute_map",),
            ("compute_fronts",),
            ("balance_fronts",),
        ]

## unigoal methods
def balance_fronts(dom):
    debug("Balancing fronts...")
    state: MovementState = dom.moving

    if state.view.size <= 1:
        return []

    if len(state.fronts) == 0:
        return []
    
    assert len(state.fronts) > 0, f"No front territories to move to! {state.fronts}"

    return [
        ("compute_free",),
        ("check_for_free",),
    ]


def balance(dom, network):
    state: MovementState = dom.moving
    debug(f"Balancing network {network}...")
    view = state.network_map.view(network)

    if view.size <= 1:
        return [("compute_balanced",), ("reset_network",)]
    else:
        return [
            ("compute_view",),
            ("compute_target",),
            ("compute_fronts",),
            ("balance_fronts",),
            ("compute_balanced",),
            ("reset_network",),
        ]


def moving(dom, arg, networks):
    state: MovementState = dom.moving
    if state.balanced == networks:
        return []
    elif state.balanced < networks and state.network is None:
        return [
            ("select_network", "networks"),
            ("moving", arg, networks),
        ]
    elif state.network is not None:
        return [
            ("balance", state.network),
            ("moving", arg, networks),
        ]
    else:
        return False


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_defensive_movement")

    include_commands()

    ## declare actions
    include_methods(
        Selector("network", "moving"),
        Computer("balanced", "moving", lambda s: s.balanced + 1),
        Reseter("network", "moving", None),
        Computer("view", "moving", compute_view),
        Computer("target", "moving", compute_target),
        Computer("fronts", "moving", compute_fronts),
        Computer("free", "moving", compute_free),
        Selector("src", "moving"),
        Selector("tgt", "moving"),
        Computer("amount", "moving", compute_amount),
        BuildStep("actions", "moving", build_step),
        Computer("map", "moving", update_map)
    )

    ghop.declare_methods(
        "check_for_free",
        check_for_free,
    )
    ghop.declare_methods(
        "balance_fronts",
        balance_fronts,
    )
    ghop.declare_methods(
        "balance",
        balance,
    )

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "moving",
        moving,
    )

    # ghop.current_domain.display()


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
    """A planner for placing troops defensively in Risk."""

    def __init__(self, player_id: int):
        super().__init__()
        self.player = player_id

    def construct_plan(self, state: GameState) -> MovementPlan:
        """Create a placement plan for the given player in the current state."""

        pstate = construct_planning_state(state, self.player)
        construct_planning_domain(state)
        final_state = ghop.run_lazy_lookahead(
            pstate, [("moving", "balanced", len(pstate.moving.networks))]
        )
        actions: list[MovementStep] = final_state.moving.actions
        debug(f"Generated actions for movement plan: {actions}")

        plan = MovementPlan(moves=len(actions))
        for action in actions:
            action: MovementStep

            path = find_movement_sequence(
                state.get_territory(action.source),
                state.get_territory(action.destination),
                action.troops,
            )

            if path is not None and len(path) >= 1:
                route = []
                for move in path:
                    route.append(MovementStep(move.src.id, move.tgt.id, move.amount))

            if route:
                plan.add_step(
                    RouteMovementStep(
                        route=route,
                        troops=action.troops,
                    )
                )

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from risk.utils.loading import load_game_state_from_file
    from logging import DEBUG
    from os.path import join

    setLevel(DEBUG)

    ghop.verbose = 0
    placements = random.randint(1, 5)

    state = GameState.create_new_game(20, 2, 1000)
    state.initialise()

    planner = MovementPlanner(0)
    plan = planner.construct_plan(state)

    info(f"Generated Movement Plan:  {plan}")

    for step in plan.steps:
        info(step)
