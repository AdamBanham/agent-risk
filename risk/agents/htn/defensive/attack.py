from risk.agents.plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug

from risk.agents.htn import gtpyhop as ghop
from ..bases import Selector, HTNStateWithPlan, BuildStep, Computer, Filter

import random
from dataclasses import dataclass, field
from typing import List, Collection


@dataclass
class AttackState(HTNStateWithPlan):
    max_attacks: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronts: List[mapping.SafeNode] = None
    attacker: mapping.SafeNode = None
    adjacents: List[mapping.SafeNode] = field(default_factory=list)
    defender: mapping.SafeNode = None
    troops: int = 0
    actions: List[AttackStep] = field(default_factory=list)


## actions
def filter_fronts(
    state: AttackState, collection: Collection[mapping.SafeNode]
) -> Collection[mapping.SafeNode]:

    # for each frontline, check if they have an adjacent
    # enemy territory with a safe attack
    ret = []
    for node in collection:
        adj_enemies = [
            adj
            for adj in state.map.get_adjacent_nodes(node.id)
            if adj.owner != state.player
            and max(adj.value + 5, adj.value * 3)
            < (state.map.get_node(node.id).value - 1)
        ]
        debug(f"filter_fronts:: node {node.id} has adj_enemies: {adj_enemies}")
        if adj_enemies:
            ret.append(node)

    return ret


def compute_adjacents(state: AttackState) -> List[mapping.SafeNode]:
    front = state.attacker
    adj_enemies = [
        adj
        for adj in state.map.get_adjacent_nodes(front.id)
        if adj.owner != state.player
        and max(adj.value + 5, adj.value * 3)
        < (state.map.get_node(front.id).value - 1)
    ]
    return adj_enemies


def compute_troops(state: AttackState) -> int:
    front = state.attacker
    adj = state.defender
    safe_troop_count = max(adj.value + 5, adj.value * 3)
    return safe_troop_count


def construct_step(state: AttackState) -> AttackStep:
    return AttackStep(
        attacker=state.attacker.id,
        defender=state.defender.id,
        troops=state.troops,
    )


def filter_attacker(state: AttackState) -> List[mapping.SafeNode]:
    return [f for f in state.fronts if f.id != state.attacker.id]


## unigoal methods
def attacking(dom, arg, tgt):
    state: AttackState = dom.attacking
    if len(state.safe_map.frontline_nodes) == 0:
        return False
    elif state.fronts is None and state.placed != 1:
        return [
            ("filter_fronts", state.safe_map.frontline_nodes),
            ("attacking", arg, tgt),
        ]
    elif len(state.fronts) == 0 and state.placed != 1:
        return [("compute_placed",)]
    elif len(state.actions) < state.max_attacks and state.placed != 1:
        return [
            ("select_attacker", "fronts"),
            ("compute_adjacents",),
            ("select_defender", "adjacents"),
            ("compute_troops",),
            ("build_step",),
            ("compute_fronts",),
            ("attacking", arg, tgt),
        ]
    elif len(state.actions) == state.max_attacks:
        return [("compute_placed",)]
    else:
        return False


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_defensive_attack")

    ## declare actions
    ghop.declare_actions(
        Filter("fronts", "attacking", filter_fronts),
        Selector("attacker", "attacking"),
        Computer("adjacents", "attacking", compute_adjacents),
        Selector("defender", "attacking"),
        Computer("troops", "attacking", compute_troops),
        Computer("placed", "attacking", lambda s: 1),
        Computer("fronts", "attacking", filter_attacker),
        BuildStep("actions", "attacking", construct_step),
    )

    ## declear unigoal methods
    ghop.declare_unigoal_methods("attacking", attacking)


def construct_planning_state(state: GameState, player: int, max_attacks: int):
    new_map = state.map.clone()
    safe_map = mapping.construct_safe_view(new_map, player)

    placement_state = AttackState(
        player=player,
        max_attacks=max_attacks,
        map=new_map,
        safe_map=safe_map,
    )

    state = ghop.State(
        "attacking",
        attacking=placement_state,
    )

    return state


class AttackPlanner(Planner):
    """A planner for determining attacks in a defensive manner."""

    def __init__(self, player_id: int, max_attacks: int = 10):
        super().__init__()
        self.player = player_id
        self.max_attacks = max_attacks

    def construct_plan(self, state: GameState) -> AttackPlan:
        """Creates an attack plan for the given player in the current state."""

        plan = AttackPlan(self.max_attacks)

        pstate = construct_planning_state(state, self.player, self.max_attacks)
        construct_planning_domain(state)
        final_state = ghop.run_lazy_lookahead(pstate, [("attacking", "placed", 1)])
        actions = final_state.attacking.actions
        debug(f"Generated actions for attacks plan: {actions}")

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
    picks = set()
    for _ in range(3):
        terr = random.choice(terrs)
        terr = state.get_territory(terr.id)
        terr.armies += 150
        info(
            f"Modified territory to have highest armies: {terr.id} with {terr.armies} armies, owned by player {terr.owner}"
        )
    state.update_player_statistics()

    planner = AttackPlanner(0, 10)
    plan = planner.construct_plan(state)

    info(f"Generated Attack Plan: {plan}")
    seen = set()
    for step in plan.steps:
        info(step)
        defender_army = state.map.get_node(step.defender).value
        info(
            f"  Defender {step.defender} has {defender_army} armies, Attacker {step.attacker} attacks with {step.troops} troops"
        )
        assert step.troops > defender_army, (
            f"Attacking troops {step.troops} should be greater than "
            f"defender armies {defender_army}"
        )
        assert max(defender_army + 5, defender_army * 3) < (
            state.map.get_node(step.attacker).value - 1
        ), (
            f"Attacker {step.attacker} does not have enough armies to safely attack "
            f"defender {step.defender}"
        )
        seen.add(step.attacker)

    assert picks < seen, f"Expected all picks in seen :: {picks} vs {seen}"