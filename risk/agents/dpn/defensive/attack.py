from ...plans import AttackStep, AttackPlan, Planner
from ..bases import GuardedTransition, ExpressiveSimProblem
from risk.utils import map as mapping

import random
from typing import Set

from simpn.helpers import Place
from simpn.simulator import SimToken, SimTokenValue


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
    for front in fronts:
        terrs.put(SimTokenValue(front, armies=map.get_node(front).value))

    class Adjacents(Place):
        model = problem
        name = "adjacents"
        amount = 0

    adjs = problem.var("adjacents")
    for front in fronts:
        neighbors = map.get_adjacent_nodes(front)
        for neighbor in neighbors:
            adjs.put(
                SimTokenValue(
                    "adjacent-{}-{}".format(front, neighbor.id),
                    adj=front,
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
        outgoing = ["adjacents", "actions"]

        def behaviour(start, terr: SimTokenValue, adj: SimTokenValue):
            safe_troop_count = max(adj.armies + 5, adj.armies * 3)
            return [
                SimToken(adj),
                SimToken(
                    SimTokenValue(
                        start,
                        action=AttackStep(terr.id, adj.identify, safe_troop_count),
                    )
                ),
            ]

        def guard(start: str, terr: SimTokenValue, adj: SimTokenValue):
            if adj.adj != terr.id:
                return False
            if adj.owner == player:
                return False
            safe_troop_count = max(adj.armies + 5, adj.armies * 3)
            if (terr.armies - 1) <= safe_troop_count:
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

        sim = create_problem(
            self.player,
            set(t.id for t in safe_map.frontline_nodes),
            state.map,
            self.attacks,
        )

        while sim.step():
            pass

        actions = sim.var("actions").marking
        actions = list(act for act in actions)
        random.shuffle(actions)
        actions = actions[: self.attacks]
        for token in actions:
            step: AttackStep = token.value.action
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG

    setLevel(DEBUG)

    from simpn.visualisation import Visualisation

    game_state = GameState.create_new_game(25, 2, 200)
    game_state.initialise()
    safe_map = mapping.construct_safe_view(game_state.map, 0)
    front = random.choice(safe_map.frontline_nodes)
    game_state.get_territory(front.id).armies = 200
    game_state.update_player_statistics()

    vis = Visualisation(
        create_problem(
            0, set(t.id for t in safe_map.frontline_nodes), game_state.map, 2
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
