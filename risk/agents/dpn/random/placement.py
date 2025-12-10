from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState
from risk.utils.logging import debug

from typing import Set
import random

from simpn.helpers import Place, Transition
from simpn.simulator import SimTokenValue, SimToken
from ..bases import ExpressiveSimProblem as SimProblem
from ..bases import GuardedTransition


def create_simulator(placements: int, terrs: Set[int]) -> SimProblem:

    problem = SimProblem()

    class Placements(Place):
        model = problem
        name = "placements"
        amount = placements

    class Territories(Place):
        model = problem
        name = "territories"

    territories = problem.var("territories")
    for terr in terrs:
        territories.put(SimTokenValue(f"terr-{terr}", territory=terr))

    class GeneratePlacement(Transition):
        model = problem
        name = "generate-placement"
        incoming = ["placements", "territories"]
        outgoing = ["territories", "actions"]

        def behaviour(tok_val: SimTokenValue, terr_val: SimTokenValue):
            action_val = SimTokenValue(
                f"place-{1}-on-{terr_val.territory}",
                territory=terr_val.territory,
                troops=1,
            )
            return [SimToken(terr_val.clone()), SimToken(action_val)]

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
    from logging import DEBUG
    from risk.utils.logging import setLevel
    setLevel(DEBUG)

    state = GameState.create_new_game(52, 2, 50)
    state.initialise()
    state.update_player_statistics()

    for placement in [random.randint(0, 10) for _ in range(10)]:
        player = random.randint(0, 1)
        planner = RandomPlacement(player_id=player, placements=placement)

        plan = planner.construct_plan(state)
        debug(plan)
        count = 0
        assert len(plan.steps) == placement, \
            "Expected {} placements, got {}".format(
                placement, len(plan.steps)
        )
        for step in plan.steps:
            debug(step)
            assert state.map.get_node(step.territory).owner == planner.player_id, \
                "Territory {} not owned by player {}".format(player)
            count += step.troops
        assert count == placement, \
            "Expected {} total troops, got {}".format(
            placement, count
        )
