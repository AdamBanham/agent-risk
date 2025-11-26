from risk.agents.plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.movement import find_movement_sequence
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
    Reseter,
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
    options: List[tuple[mapping.NetworkNode, int]] = field(default_factory=list)
    free: List[mapping.NetworkNode] = field(default_factory=list)
    tgt: tuple[mapping.NetworkNode, int] = None
    src: mapping.NetworkNode = None
    amount: int = 0
    target: int = -1
    actions: List[MovementStep] = field(default_factory=list)


def sum_of_adjacents(node: mapping.SafeNode, map: mapping.Graph, player: int) -> int:
    total = 0
    for neighbor in map.get_adjacent_nodes(node.id):
        if neighbor.owner != player:
            total += (1.0 / neighbor.value) * 10
    return total


## commands
def compute_options(state: MovementState):
    map = state.map
    network_map = state.view
    network = state.network

    fronts = network_map.frontlines_in_network(network)
    movable_armies = sum(map.get_node(node.id).value for node in network_map.nodes)
    movable_armies -= network_map.size
    debug(
        f"Computing options for network {network} with total armies {movable_armies} and view size {network_map.size}..."
    )
    weights = [sum_of_adjacents(node, map, state.player) for node in fronts]

    # sort them to keep only the top three positions
    top_most = random.randint(1, min(3, len(fronts)))
    options = sorted(
        zip(fronts, weights),
        key=lambda x: x[1],
        reverse=True,
    )[:top_most]

    # normalize weights and assign troops
    total_weight = sum(w for f, w in options)
    options = [(f, w / total_weight) for f, w in options]
    options = [(f, max(1, int(movable_armies * w))) for f, w in options]

    # sort by most important frontline first
    ordered_fronts = sorted(
        options,
        key=lambda x: x[1],
        reverse=True,
    )

    return ordered_fronts


def compute_free(state: MovementState):
    map = state.map
    network_map = state.view

    free = []
    for node in network_map.nodes:
        if map.get_node(node.id).value > 1 and not any(
            f.id == node.id for f, _ in state.options
        ):
            free.append(node)
        elif any(
            f.id == node.id and map.get_node(f.id).value >= w for f, w in state.options
        ):
            free.append(node)

    return free


def filter_free(
    state: MovementState, collection: Collection[mapping.NetworkNode]
) -> Collection[mapping.NetworkNode]:
    filtered = []
    map = state.map
    for node in collection:
        if node.id != state.tgt[0].id:
            filtered.append(node)
    return filtered


def compute_amount(state: MovementState):
    src = state.src
    tgt, wanted = state.tgt
    map = state.map
    wanted = wanted - map.get_node(tgt.id).value

    available = map.get_node(src.id).value - 1
    amount = min(available, wanted)

    return amount


def construct_step(state: MovementState) -> MovementStep:
    return MovementStep(
        source=state.src.id,
        destination=state.tgt[0].id,
        troops=state.amount,
    )


def compute_map(state: MovementState):
    new_map = state.map.clone()
    src = state.src
    tgt, _ = state.tgt
    troops = state.amount

    new_map.get_node(src.id).value -= troops
    new_map.get_node(tgt.id).value += troops

    return new_map


def filter_options(
    state: MovementState, collection: Collection[tuple[mapping.NetworkNode, int]]
) -> Collection[tuple[mapping.NetworkNode, int]]:
    filtered = []
    map = state.map
    for option in collection:
        node, wanted = option
        if map.get_node(node.id).value < wanted:
            filtered.append(option)
    return filtered


## methods
def balance(dom):
    state: MovementState = dom.moving
    if len(state.free) == 0:
        return [("compute_balanced",)]
    else:
        return [
            ("select_tgt", "options"),
            ("filter_free", "free"),
            ("select_src", "free"),
            ("compute_amount",),
            ("build_step",),
            ("compute_map",),
            ("filter_options", "options"),
            ("handle_options",),
        ]


def handle_options(dom):
    state: MovementState = dom.moving
    if len(state.options) == 0:
        return [("compute_balanced",)]
    else:
        return [
            ("compute_free",),
            ("balance",),
        ]


def check_network(
    dom,
):
    state: MovementState = dom.moving
    if (
        state.network_map.view(state.network).size < 2
        or len(state.network_map.frontlines_in_network(state.network)) == 0
    ):
        return [("compute_balanced",)]
    else:
        return [
            ("compute_view",),
            ("compute_options",),
            ("filter_options", "options"),
            ("handle_options",),
        ]


## goal
def decide_moves(dom, arg, places):
    state: MovementState = dom.moving
    if len(state.networks) == 0:
        return []
    else:
        return [
            ("select_network", "networks"),
            ("filter_networks", "networks"),
            ("check_network",),
            ("moving", arg, places),
        ]


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_aggressive_movement")

    include_commands()

    ## declare actions
    include_methods(
        Selector("network", "moving"),
        Filter("networks", "moving", lambda s, c: [e for e in c if e != s.network]),
        Computer("options", "moving", compute_options),
        Computer("balanced", "moving", lambda s: s.balanced + 1),
        Computer("view", "moving", lambda s: s.network_map.view(s.network)),
        Computer("free", "moving", compute_free),
        Filter("free", "moving", filter_free),
        Selector("tgt", "moving"),
        Selector("src", "moving"),
        Computer("amount", "moving", compute_amount),
        BuildStep("actions", "moving", construct_step),
        Computer("map", "moving", compute_map),
        Filter("options", "moving", filter_options),
        handle_options,
        balance,
        check_network,
    )

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

    def __init__(
        self,
        player_id: int,
    ):
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
    from logging import DEBUG

    setLevel(DEBUG)

    ghop.verbose = 0
    max_attacks = random.randint(1, 5)

    state = GameState.create_new_game(50, 2, 1000)
    state.initialise()

    planner = MovementPlanner(0)
    plan = planner.construct_plan(state)

    info(f"Generated Movement Plan:  {plan}")
    for step in plan.steps:
        info(step)
