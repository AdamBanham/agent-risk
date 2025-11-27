from ...plans import TroopPlacementStep, PlacementPlan, Planner
from ..bases import ExpressiveSimProblem
from risk.utils import map as mapping

import random
from typing import Set

from simpn.helpers import Place, Transition
from simpn.simulator import SimToken, SimTokenValue


def create_problem(
    player: int, fronts: Set[int], placements: int
) -> ExpressiveSimProblem:
    """
    Constructs a SimProblem for deciding placements.
    """

    problem = ExpressiveSimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = placements

    class Territories(Place):
        model = problem
        name = "territories"

    terrs = problem.var("territories")
    for front in fronts:
        terrs.put(SimTokenValue(front))

    class Actions(Place):
        model = problem
        name = "actions"
        amount = 0

    class PlaceTroops(Transition):
        model = problem
        name = "place-troops"
        incoming = ["start", "territories"]
        outgoing = ["territories", "actions"]

        def behaviour(start, terr: SimTokenValue):

            return [
                SimToken(terr),
                SimToken(SimTokenValue(start, action=TroopPlacementStep(terr.id, 1))),
            ]

    return problem


class PlacementPlanner(Planner):
    """
    A planner for deciding defensive placements using DPNs.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, state):

        plan = PlacementPlan(self.placements)
        safe_map = mapping.construct_safe_view(state.map, self.player)
        n_most = random.randint(1, len(safe_map.frontline_nodes))
        top_most = sorted(
            safe_map.frontline_nodes,
            key=lambda t: state.map.get_node(t.id).value,
            reverse=True,
        )[: int(n_most)]

        sim = create_problem(
            self.player,
            set(t.id for t in top_most),
            self.placements,
        )

        while sim.step():
            pass

        actions = sim.var("actions").marking
        for token in actions:
            step: TroopPlacementStep = token.value.action
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG

    from simpn.visualisation import Visualisation

    vis = Visualisation(create_problem(0, {1, 2, 3, 4, 5}, 10))
    vis.show()

    setLevel(DEBUG)

    game_state = GameState.create_new_game(25, 2, 50)
    game_state.initialise()

    for _ in range(10):
        planner = PlacementPlanner(player=0, placements=random.randint(1, 10))
        plan = planner.construct_plan(game_state)

        info(
            f"Constructed Placement Plan: {plan},"
            + f" expected placements: {planner.placements}"
        )
        for step in plan.steps:
            info(f"Step: {step}")

        input("Press Enter to continue...")
