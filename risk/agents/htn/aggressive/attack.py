from risk.agents.plans import Planner, AttackPlan, AttackStep
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
class AttackState(HTNStateWithPlan):
    max_attacks: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronter: mapping.SafeNode = None
    looked: bool = False
    adjacents: List[mapping.Node] = None
    attacker: mapping.Node = None
    defender: mapping.Node = None
    troops: int = -1
    actions: List[AttackStep] = field(default_factory=list)
    had_safe: bool = None


def sum_of_adjacents(node: mapping.SafeNode, map: mapping.Graph, player: int) -> float:
    total = 0
    armies = map.get_node(node.id).value
    for neighbor in map.get_adjacent_nodes(node.id):
        if neighbor.owner != player:
            total += armies / neighbor.value
    return total


def strength(o: mapping.Node) -> float:
    return o.value


## commands
def compute_fronter(state: AttackState):
    fronts = state.safe_map.frontline_nodes
    if len(fronts) == 0:
        return None

    fronts = sorted(
        fronts,
        key=lambda node: sum_of_adjacents(node, state.map, state.player),
        reverse=True,
    )

    fronter = fronts[0]
    if sum_of_adjacents(fronter, state.map, state.player) > 0.25:
        return fronter
    else:
        return None

def check_adjacents(state: AttackState):
    has_safe = False
    attacker = state.map.get_node(state.fronter.id).value
    for adj in state.adjacents:
        safe_troops = max(adj.value + 5, adj.value * 3)
        has_safe = has_safe or attacker >= safe_troops
    return has_safe

def compute_looked(state: AttackState):
    return True


def compute_troops(state: AttackState):
    if state.troops == -1:
        attacker = state.map.get_node(state.fronter.id)
        return attacker.value - 1
    else:
        return state.troops // 2


def compute_adjacents(state: AttackState):
    ret = []
    for adj in state.map.get_adjacent_nodes(state.attacker.id):
        if adj.owner != state.player:
            ret.append(adj)
    return ret


def filter_adjacents(state: AttackState, adjacents: Collection[mapping.Node]):
    adjacents = sorted(adjacents, key=strength)
    return [adjacents[0]]


def construct_step(state: AttackState) -> AttackStep:
    return AttackStep(
        attacker=state.attacker.id,
        defender=state.defender.id,
        troops=state.troops,
    )


def compute_attacker(state: AttackState):
    return state.map.get_node(state.defender.id)


def compute_map(state: AttackState):
    map = state.map.clone()

    map.get_node(state.attacker.id).value -= state.troops
    map.get_node(state.defender.id).value = state.troops
    map.get_node(state.defender.id).owner = state.player

    return map


## methods
def continue_attack(dom):
    state: AttackState = dom.attacking
    if len(state.actions) >= state.max_attacks:
        return []
    elif state.troops < 2:
        return []
    elif state.troops // 2 < 1:
        return []
    else:
        return [
            ("find_attack",),
        ]


def should_attack(dom):
    state: AttackState = dom.attacking

    if len(state.adjacents) == 0:
        return []
    elif len(state.actions) == 0 and state.had_safe is None:
        return [
            ("compute_had_safe",),
            ("should_attack",)
        ]
    elif state.had_safe:
        return [
            ("filter_adjacents", "adjacents"),
            ("select_defender", "adjacents"),
            ("compute_troops",),
            ("build_step",),
            ("compute_attacker",),
            ("compute_map",),
            ("continue_attack",),
        ]
    else:
        return [

        ]


def find_attack(
    dom,
):
    return [
        ("compute_adjacents",),
        ("should_attack",),
    ]


## goal
def decide_attacks(dom, arg, places):
    state: AttackState = dom.attacking
    if not state.looked:
        return [
            ("compute_fronter",),
            ("compute_looked",),
            ("attacking", arg, places),
        ]
    elif state.fronter is None or state.map.get_node(state.fronter.id).value < 2:
        return [("compute_placed",)]
    else:
        return [
            ("c_set", "attacking", "attacker", state.map.get_node(state.fronter.id)),
            ("find_attack",),
            ("compute_placed",),
        ]


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_aggressive_attacks")

    include_commands()

    ## declare actions
    include_methods(
        Computer("fronter", "attacking", compute_fronter),
        Computer("looked", "attacking", compute_looked),
        Computer("placed", "attacking", lambda s: 1),
        Computer("troops", "attacking", compute_troops),
        Computer("adjacents", "attacking", compute_adjacents),
        Filter("adjacents", "attacking", filter_adjacents),
        Selector("defender", "attacking"),
        BuildStep("actions", "attacking", construct_step),
        Computer("attacker", "attacking", compute_attacker),
        Computer("map", "attacking", compute_map),
        Computer("had_safe", "attacking", check_adjacents),
        find_attack,
        continue_attack,
        should_attack,
    )

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "attacking",
        decide_attacks,
    )


def construct_planning_state(
    state: GameState, player: int, max_attacks: int
) -> ghop.State:
    new_map = state.map.clone()
    safe_map = mapping.construct_safe_view(new_map, player)

    attack_state = AttackState(
        max_attacks=max_attacks,
        player=player,
        map=new_map,
        safe_map=safe_map,
    )

    state = ghop.State(
        "attacks",
        attacking=attack_state,
    )

    return state


class AttackPlanner(Planner):
    """
    Aggressive attack planner for troops in Risk.
    """

    def __init__(self, player_id: int, max_attacks: int):
        super().__init__()
        self.player = player_id
        self.max_attacks = max_attacks

    def construct_plan(self, state: GameState) -> AttackPlan:
        """Create an attack plan for the given player in the current state."""

        plan = AttackPlan(self.max_attacks)

        pstate = construct_planning_state(state, self.player, self.max_attacks)
        construct_planning_domain(state)
        final_state = ghop.run_lazy_lookahead(pstate, [("attacking", "placed", 1)])
        actions = final_state.attacking.actions
        debug(f"Generated actions for attack plan: {actions}")

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

    info(f"Generated Attack Plan:: {plan}")
    for step in plan.steps:
        info(step)
