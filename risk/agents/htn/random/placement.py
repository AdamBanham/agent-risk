from risk.agents.htn import gtpyhop as ghop
from ..bases import HTNStateWithPlan
from risk.state import Territory
from ...plans import PlacementPlan, TroopPlacementStep

from typing import Set
from dataclasses import dataclass, field
import random


@dataclass
class PlacementState(HTNStateWithPlan):
    placements: int = 0
    territories: Set[int] = field(default_factory=set)
    placed: int = 0
    terr: Territory = None
    troops: int = 0


### actions
def select_terr(dom, territories: Set[int] = None):
    state: PlacementState = dom.placing
    if territories:
        state.terr = random.choice(list(territories))
        return dom


def select_troops(dom, places: int = 0):
    state: PlacementState = dom.placing
    if places > 0:
        state.troops = random.choice(range(1, places + 1))
        return dom


def add_to_plan(dom, plan: PlacementPlan = None):
    state: PlacementState = dom.placing
    step = TroopPlacementStep(
        territory=state.terr,
        troops=state.troops,
    )
    plan.add_step(step)
    state.placed += state.troops
    state.plan = plan
    return dom


### methods
def drop_placements(dom, arg, places):
    state: PlacementState = dom.placing
    if not state.plan.goal_achieved(None):
        return [
            ("select_terr", state.territories),
            ("select_troops", state.placements - state.placed),
            ("add_to_plan", state.plan),
            ("placing", arg, places),
        ]
    else:
        return False


def stop_placements(dom, arg, places):
    state: PlacementState = dom.placing
    if state.plan.goal_achieved(None):
        return []
    else:
        return False


### helpers


def create_state(player: int, placements: int, territories: Set[int]) -> object:

    dom = ghop.State(
        "placements",
        **{
            "placing": PlacementState(
                player=player,
                placements=placements,
                territories=territories,
                plan=PlacementPlan(placements),
                placed=0,
            )
        },
    )

    return dom


def create_planner():
    ghop.current_domain = ghop.Domain("htn_random_placement")
    ghop.declare_actions(select_terr, select_troops, add_to_plan)
    ghop.declare_unigoal_methods("placing", drop_placements, stop_placements)


class RandomPlacements:
    """
    Randomly selects territories and troop placements.
    """

    @staticmethod
    def construct_plan(
        player: int, placements: int, territories: Set[int]
    ) -> PlacementPlan:
        
        create_planner()
        dom = create_state(player, placements, territories)
        _ = ghop.find_plan(dom, [("placing", "placed", placements)])

        return dom.placing.plan


if __name__ == "__main__":

    ghop.verbose = 0

    placements = random.randint(1, 15)

    territories = random.sample(range(1, 11), k=5)

    plan = RandomPlacements.construct_plan(
        player=0, placements=placements, territories=set(territories)
    )

    print(f"Generated Placement Plan: {str(plan)}")
    troops = 0
    for step in plan.steps:
        troops += step.troops
        print(step)
    assert troops == placements
