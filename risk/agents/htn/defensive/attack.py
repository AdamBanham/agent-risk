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
class AttackState(HTNStateWithPlan):
    max_attacks: int = 0
    placed: int = 0
    map: mapping.Graph = None
    safe_map: mapping.SafeGraph = None
    fronts: List[mapping.SafeNode] = field(default_factory=list)
    attacker: mapping.SafeNode = None
    adjacents: List[mapping.SafeNode] = field(default_factory=list)
    defender: mapping.SafeNode = None
    troops: int = 0
    actions: List[MovementStep] = field(default_factory=list)


def construct_planning_domain(state: GameState):
    ghop.current_domain = ghop.Domain("htn_defensive_attack")

    ## declare actions
    ghop.declare_actions()

    ## declear unigoal methods
    ghop.declare_unigoal_methods(
        "attacking",
        ...,
    )


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
        "attack",
        attacking=placement_state,
    )

    return state


class AttackPlanner(Planner):
    """A planner for determining attacks in a defensive manner."""

    def __init__(self, player_id: int, max_attacks: int = 10):
        super().__init__()
        self.player = player_id
        self.max_attacks = max_attacks

    def construct_plan(self, state: GameState) -> MovementPlan:
        """Creates an attack plan for the given player in the current state."""

        plan = MovementPlan()

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
    terr = random.choice(terrs)
    terr = state.get_territory(terr.id)
    terr.armies += 150
    info(
        f"Modified territory to have highest armies: {terr.id} with {terr.armies} armies, owned by player {terr.owner}"
    )
    state.update_player_statistics()

    planner = AttackPlanner(0, 1)
    plan = planner.construct_plan(state)

    print("Generated Attck Plan:", plan)

    for step in plan.steps:
        print(step)
