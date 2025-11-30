from ...plans import Planner, TroopPlacementStep, PlacementPlan
from risk.utils import map as mapping
from risk.state import GameState

from typing import Set
from ..bases import ExpressiveSimProblem
from simpn.simulator import SimTokenValue, SimToken
from simpn.helpers import Place, BPMN

import random


def construct_problem(fronts: Set[int], map: mapping.SafeGraph, placements: int):

    problem = ExpressiveSimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = 0

    start = problem.var("start")
    start.put(
        SimTokenValue(
            "start-0",
            fronts=fronts,
            map=map,
            placements=placements,
        )
    )

    class Planner(BPMN):
        model = problem
        type = "resource-pool"
        name = "planner"
        amount = 0

    planner = problem.var("planner")
    planner.put(SimTokenValue("planner-0", actions=[]))

    class FilterFronts(BPMN):
        model = problem
        type = "task"
        incoming = ["start", "planner"]
        outgoing = ["filtered", "planner"]
        name = "Filter Fronts"

        def behaviour(val, res):
            val = val.clone()

            n_most = random.randint(1, len(val.fronts))
            top_most = sorted(
                val.fronts,
                key=lambda t: val.map.get_node(t).value,
                reverse=True,
            )[: int(n_most)]

            val.fronts = set(f for f in top_most)
            return [SimToken((val, res))]

    class ReworkXorJoin(BPMN):
        model = problem
        type = "gat-ex-join"
        incoming = ["filtered", "rework"]
        outgoing = ["placing"]
        name = "Rework Join"

    class Placer(BPMN):
        model = problem
        type = "task"
        incoming = ["placing", "planner"]
        outgoing = ["placed", "planner"]
        name = "Place Troop"

        def behaviour(val, res):

            res = res.clone()
            val = val.clone()

            front = random.choice(list(val.fronts))
            res.actions.append(
                TroopPlacementStep(
                    territory=front,
                    troops=1,
                )
            )
            val.placements -= 1

            return [SimToken((val, res))]

    class ReworkXorSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        incoming = ["placed"]
        outgoing = ["finishing", "rework"]
        name = "Rework Split"

        def choice(token: SimTokenValue):
            if token.placements == 0:
                return [SimToken(token), None]
            else:
                return [None, SimToken(token)]

    class Completed(BPMN):
        model = problem
        type = "end"
        incoming = ["finishing"]
        name = "Completed Plan"

    return problem


class PlacementPlanner(Planner):
    """
    Planner for aggressive placing troops.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, state: GameState):
        plan = PlacementPlan(self.placements)

        safemap = mapping.construct_safe_view(state.map, self.player)

        problem = construct_problem(
            set(f.id for f in safemap.frontline_nodes),
            state.map.clone(),
            self.placements,
        )

        while problem.step():
            pass

        planner = problem.var("planner")
        actions = planner.marking[0].value.actions

        for step in actions:
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from risk.state import GameState
    from logging import DEBUG

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    state = GameState.create_new_game(20, 2, 100)
    state.initialise()
    state.update_player_statistics()

    safemap = mapping.construct_safe_view(state.map, 0)
    fronts = safemap.frontline_nodes

    problem = construct_problem(set(f.id for f in fronts), state.map.clone(), 2)

    vis = Visualisation(problem)
    vis.show()

    for _ in range(10):
        pick = random.randint(1, 5)
        planner = PlacementPlanner(0, pick)
        plan = planner.construct_plan(state)

        print(plan)
        assert len(plan.steps) == pick, "Expected 2 placement steps in the plan."
        for step in plan.steps:
            print(step)
        input("Press Enter to continue...")
