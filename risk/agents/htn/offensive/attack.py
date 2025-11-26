from risk.agents.plans import Planner, AttackPlan, AttackStep
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
class AttackState(HTNStateWithPlan):
    max_attacks: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronts: List[mapping.SafeNode] = field(default_factory=list)
    terr: mapping.SafeNode = None
    actions: List[AttackStep] = field(default_factory=list)


def decide_attacks(dom, arg, places):
    pass


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_aggressive_attacks")

    include_commands()

    ## declare actions
    include_methods()

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
        final_state = ghop.run_lazy_lookahead(
            pstate, [("attacking", "placed", 1)]
        )
        actions = final_state.attacking.actions
        debug(f"Generated actions for attack plan: {actions}")

        for action in actions:
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
