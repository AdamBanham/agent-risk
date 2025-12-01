from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.utils import map as mapping
from risk.state import GameState

import random

from ..bases import ExpressiveSimProblem
from simpn.simulator import SimTokenValue, SimToken
from simpn.helpers import Place, BPMN


def sum_of_adjacents(node: int, map: mapping.Graph, player: int) -> int:
    total = 0
    armies = map.get_node(node).value
    for neighbor in map.get_adjacent_nodes(node):
        if neighbor.owner != player:
            total += armies / neighbor.value
    return total


def construct_problem(
    fronts: set[int], map: mapping.Graph, player: int, placements: int
):

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
        )
    )

    class Planner(Place):
        model = problem
        name = "planner"
        amount = 0

    planner = problem.var("planner")
    planner.put(SimTokenValue("planner-0", actions=[]))

    class SelectFronter(BPMN):
        model = problem
        type = "task"
        incoming = ["start", "planner"]
        outgoing = ["selected", "planner"]
        name = "Select Front"

        def behaviour(val, res):
            val.clone()
            sorted_fronts = sorted(
                val.fronts,
                key=lambda t: sum_of_adjacents(t, val.map, player=player),
                reverse=True,
            )
            val.front = sorted_fronts[0]
            return [SimToken((val, res))]

    class PlaceTroops(BPMN):
        model = problem
        type = "task"
        incoming = ["selected", "planner"]
        outgoing = ["finishing", "planner"]
        name = "Place Troops"

        def behaviour(val, res):
            res.clone()
            res.actions.append(TroopPlacementStep(val.front, placements))
            return [SimToken((val, res))]

    class End(BPMN):
        model = problem
        type = "end"
        incoming = ["finishing"]
        name = "Finished"

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

        problem = construct_problem(
            set(
                f.id
                for f in mapping.construct_safe_view(
                    state.map, self.player
                ).frontline_nodes
            ),
            state.map.clone(),
            self.player,
            self.placements,
        )

        while problem.step():
            pass

        actions = problem.var("planner").marking[0].value.actions

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

    problem = construct_problem(set(f.id for f in fronts), state.map.clone(), 0, 2)

    vis = Visualisation(problem)
    vis.show()

    for _ in range(10):
        pick = random.randint(1, 5)
        planner = PlacementPlanner(0, pick)
        plan = planner.construct_plan(state)

        print(plan)
        assert len(plan.steps) == 1, "Expected 1 placement steps in the plan."
        for step in plan.steps:
            print(step)
        input("Press Enter to continue...")
