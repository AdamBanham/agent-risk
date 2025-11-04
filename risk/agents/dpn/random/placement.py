from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState

from typing import Set
import random

from simpn.helpers import Place, Transition
from simpn.simulator import SimTokenValue, SimToken
from .base import ExpressiveSimProblem as SimProblem
from .base import GuardedTransition


def create_simulator(placements: int, terrs: Set[int]) -> SimProblem:

    problem = SimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = 1

    class Territories(Place):
        model = problem
        name = "territories"

    territories = problem.var("territories")
    for terr in terrs:
        territories.put(SimTokenValue(f"terr-{terr}", territory=terr))

    class SetPlacements(Transition):
        model = problem
        name = "set-placements"
        incoming = ["start"]
        outgoing = ["placements"]

        def behaviour(tok_val):
            new_val = SimTokenValue(tok_val, placements=placements)
            return [SimToken(new_val)]

    class CompletePlan(GuardedTransition):
        model = problem
        name = "complete-plan"
        incoming = ["placements"]
        outgoing = ["done"]

        def guard(tok_val: SimTokenValue):
            if tok_val.placements == 0:
                return True
            return False

        def behaviour(tok_val: SimTokenValue):
            return [SimToken(tok_val)]

    class GeneratePlacement(GuardedTransition):
        model = problem
        name = "generate-placement"
        incoming = ["placements", "territories"]
        outgoing = ["placements", "territories", "actions"]

        def guard(tok_val: SimTokenValue, terr_val: SimTokenValue):
            if tok_val.placements > 0:
                return True
            return False

        def behaviour(tok_val: SimTokenValue, terr_val: SimTokenValue):
            pick = random.randint(1, tok_val.placements)
            new_val = tok_val.clone()
            new_val.placements -= pick
            action_val = SimTokenValue(
                f"place-{pick}-on-{terr_val.territory}",
                territory=terr_val.territory,
                troops=pick,
            )
            return [SimToken(new_val), SimToken(terr_val), SimToken(action_val)]

    return problem


class RandomPlacement(Planner):
    """
    A planner that generates random placement plans.
    """

    def __init__(self, player_id: int = None, placements: int = None):
        super().__init__()
        self.player_id = player_id
        self.placements = placements

    def construct_plan(self, state: GameState) -> "PlacementPlan":
        # Implement logic to create a random placement plan
        terrs = state.get_territories_owned_by(self.player_id)
        terrs = set([t.id for t in terrs])
        sim = create_simulator(self.placements, terrs)

        while sim.step() is not None:
            pass

        plan = PlacementPlan(self.placements)
        for tok in sim.var("actions").marking:
            plan.add_step(
                TroopPlacementStep(
                    territory=tok.value.territory,
                    troops=tok.value.troops,
                )
            )
        return plan


if __name__ == "__main__":
    state = GameState.create_new_game(52, 2, 50)
    state.initialise()

    for placement in [random.randint(0, 10) for _ in range(10)]:
        planner = RandomPlacement(player_id=random.randint(0,1), placements=placement)
        plan = planner.construct_plan(state)

        print(plan)
        count = 0
        for step in plan.steps:
            print(step)
            count += step.troops
        print("Total troops placed:", count)
        assert count == placement
