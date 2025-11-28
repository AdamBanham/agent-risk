from ...plans import TroopPlacementStep, PlacementPlan, Planner
from ..bases import ExpressiveSimProblem
from risk.utils import map as mapping

import random
from typing import Set, Collection

from simpn.helpers import Place, Transition
from simpn.simulator import SimToken, SimTokenValue


def sum_of_adjacents(node: mapping.SafeNode, map: mapping.Graph, player: int) -> int:
    total = 0
    armies = map.get_node(node.id).value
    for neighbor in map.get_adjacent_nodes(node.id):
        if neighbor.owner != player:
            total += armies / neighbor.value
    return total


class Priority:
    """
    A priority function to sort frontline territories by their attack potential.
    """

    def __init__(self, map: mapping.Graph, player: int):
        self.map = map
        self.player = player

    @staticmethod
    def get_values(binding, var_name: str = None) -> Collection:
        """
        Helper function to extract SimTokens from a binding.
        """
        if var_name is None:
            return [tok.value for var, tok in binding[0] if isinstance(tok, SimToken)]
        else:
            ret = []
            for var, tok in binding[0]:
                if str(var) == var_name and isinstance(tok, SimToken):
                    ret.append(tok.value)
            return ret

    @staticmethod
    def get_event(self, binding) -> Collection:
        """
        Helper function to extract the event of a binding.
        """
        return binding[-1]

    def __call__(self, bindings: Collection) -> int:

        def get_val(binding) -> float:
            values = self.get_values(binding, "territories")
            if values:
                node = self.map.get_node(values[0].id)
                return sum_of_adjacents(node, self.map, self.player)
            return 0

        bindings = sorted(bindings, key=get_val, reverse=True)
        return bindings[0]


def create_problem(
    player: int, fronts: Set[int], placements: int, map: mapping.Graph
) -> ExpressiveSimProblem:
    """
    Constructs a SimProblem for deciding placements.
    """

    problem = ExpressiveSimProblem(binding_priority=Priority(map, player))

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
    A planner for deciding placements aggressively using DPNs.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, state):

        plan = PlacementPlan(self.placements)
        safe_map = mapping.construct_safe_view(state.map, self.player)

        sim = create_problem(
            self.player,
            set(t.id for t in safe_map.frontline_nodes),
            self.placements,
            state.map
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

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    game_state = GameState.create_new_game(25, 2, 50)
    game_state.initialise()
    game_state.update_player_statistics()

    safe_map = mapping.construct_safe_view(game_state.map, 0)
    fronts = set(t.id for t in safe_map.frontline_nodes)
    vis = Visualisation(create_problem(0, fronts, 10, game_state.map))
    vis.show()

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
