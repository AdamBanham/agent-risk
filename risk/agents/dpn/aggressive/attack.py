from ...plans import AttackStep, AttackPlan, Planner
from ..bases import GuardedTransition, ExpressiveSimProblem
from risk.utils import map as mapping

import random
from typing import Set, Collection

from simpn.helpers import Place
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
            values = self.get_values(binding, "adjacents")
            if values:
                node = self.map.get_node(values[0].id)
                return node.value
            return 0

        bindings = sorted(bindings, key=get_val, reverse=True)
        sel = bindings[0]

        return sel


def create_problem(
    player: int, fronts: Set[int], map: mapping.Graph, attacks: int
) -> ExpressiveSimProblem:
    """
    Constructs a SimProblem for deciding attacks.
    """

    problem = ExpressiveSimProblem()

    class Start(Place):
        model = problem
        name = "start"
        amount = attacks

    class Territories(Place):
        model = problem
        name = "territories"

    terrs = problem.var("territories")
    for node in fronts:
        terrs.put(SimTokenValue(node, armies=map.get_node(node).value))

    class Adjacents(Place):
        model = problem
        name = "adjacents"
        amount = 0

    adjs = problem.var("adjacents")
    for node in map.nodes:
        neighbors = map.get_adjacent_nodes(node.id)
        for neighbor in neighbors:
            adjs.put(
                SimTokenValue(
                    "adjacent-{}-{}".format(node.id, neighbor.id),
                    adj=node.id,
                    armies=neighbor.value,
                    owner=neighbor.owner,
                    identify=neighbor.id,
                )
            )

    class Actions(Place):
        model = problem
        name = "actions"
        amount = 0

    class AttackTerritory(GuardedTransition):
        model = problem
        name = "place-troops"
        incoming = ["start", "territories", "adjacents"]
        outgoing = ["territories", "adjacents", "actions"]

        def behaviour(start, terr: SimTokenValue, adj: SimTokenValue):
            troops = terr.armies - 1

            action = AttackStep(terr.id, adj.identify, troops)
            terr = SimTokenValue(adj.identify, armies=troops // 2)
            adj = adj.clone()
            adj.owner = player
            print(terr)
            return [
                SimToken(terr),
                SimToken(adj),
                SimToken(
                    SimTokenValue(
                        start,
                        action=action,
                    )
                ),
            ]

        def guard(start: str, terr: SimTokenValue, adj: SimTokenValue):
            if adj.adj != terr.id:
                return False
            if adj.owner == player:
                return False
            if terr.armies < 2:
                return False
            return True

    return problem


class AttackPlanner(Planner):
    """
    A planner for deciding defensive attacks using DPNs.
    """

    def __init__(self, player: int, attacks: int):
        super().__init__()
        self.player = player
        self.attacks = attacks

    def construct_plan(self, state):

        plan = AttackPlan(self.attacks)
        safe_map = mapping.construct_safe_view(state.map, self.player)

        def finder(node: mapping.SafeNode) -> float:
            return sum_of_adjacents(node, state.map, self.player)

        fronts = sorted(
            safe_map.frontline_nodes,
            key=finder,
            reverse=True,
        )
        fronter = fronts[0]
        if sum_of_adjacents(fronter, state.map, self.player) < 0.25:
            return plan

        sim = create_problem(
            self.player,
            set([fronter.id]),
            state.map.clone(),
            self.attacks,
        )

        while sim.step():
            pass

        actions = sim.var("actions").marking
        for token in reversed(actions):
            step: AttackStep = token.value.action
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    game_state = GameState.create_new_game(50, 6, 200)
    game_state.initialise()
    safe_map = mapping.construct_safe_view(game_state.map, 0)
    front = random.choice(safe_map.frontline_nodes)
    game_state.get_territory(front.id).armies = 200
    game_state.update_player_statistics()

    vis = Visualisation(
        create_problem(
            0, set([front.id]), game_state.map, 2
        )
    )
    vis.show()

    for _ in range(10):
        planner = AttackPlanner(player=0, attacks=random.randint(1, 10))
        plan = planner.construct_plan(game_state)

        info(f"Constructed Attack Plan: {plan}, expected up to: {planner.attacks}")
        for step in plan.steps:
            info(f"Step: {step}")

        input("Press Enter to continue...")
