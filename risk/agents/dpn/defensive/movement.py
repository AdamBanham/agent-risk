from ...plans import Planner, MovementStep, RouteMovementStep, MovementPlan

from ..bases import GuardedTransition, ExpressiveSimProblem
from risk.utils import map as mapping

import random
from typing import Set

from simpn.helpers import Place
from simpn.simulator import SimToken, SimTokenValue


def create_problem(player: int, map: mapping.Graph, moves: int) -> ExpressiveSimProblem:
    """
    Constructs a SimProblem for deciding moves.
    """

    problem = ExpressiveSimProblem()
    network_map = mapping.construct_network_view(map, player)

    targets = {}
    for network in network_map.networks:
        view = network_map.view(network)
        armies = sum(map.get_node(t.id).value for t in view.nodes)
        fronts = view.frontlines_in_network(network)
        movable = armies - (view.size - len(fronts))
        ideal_troops = movable // len(fronts)
        targets[network] = ideal_troops

    class Start(Place):
        model = problem
        name = "start"
        amount = moves

    class Territories(Place):
        model = problem
        name = "territories"

    terrs = problem.var("territories")
    for network in network_map.networks:
        for front in network_map.frontlines_in_network(network):
            terrs.put(
                SimTokenValue(
                    front.id, armies=map.get_node(front.id).value, network=network
                )
            )

    class Others(Place):
        model = problem
        name = "others"
        amount = 0

    adjs = problem.var("others")
    for network in network_map.networks:
        view = network_map.view(network)
        for node in view.nodes:
            adjs.put(
                SimTokenValue(
                    "other-{}-in-{}".format(node.id, network),
                    network=network,
                    armies=map.get_node(node.id).value,
                    identify=node.id,
                    safe=node.safe,
                )
            )

    class Actions(Place):
        model = problem
        name = "actions"
        amount = 0

    class MoveTroops(GuardedTransition):
        model = problem
        name = "move-troops"
        incoming = ["start", "territories", "others"]
        outgoing = ["territories", "others", "actions"]

        def behaviour(start, tgt: SimTokenValue, src: SimTokenValue):
            if src.safe:
                moving = min(src.armies - 1, targets[tgt.network] - tgt.armies)
            else:
                moving = min(
                    src.armies - targets[src.network], targets[tgt.network] - tgt.armies
                )

            tgt = tgt.clone()
            tgt.armies += moving
            src = src.clone()
            src.armies -= moving

            return [
                SimToken(tgt),
                SimToken(src),
                SimToken(
                    SimTokenValue(
                        start,
                        action=MovementStep(src.identify, tgt.id, moving),
                    )
                ),
            ]

        def guard(start: str, terr: SimTokenValue, other: SimTokenValue):
            target = targets[terr.network]
            if terr.armies < target:
                if other.network == terr.network and terr.id != other.identify:
                    if other.armies > 1:
                        if other.safe or other.armies > target:
                            return True
            return False

    return problem


class MovementPlanner(Planner):
    """
    A planner for deciding defensive movements using DPNs.
    """

    def __init__(self, player: int, moves: int):
        super().__init__()
        self.player = player
        self.moves = moves

    def construct_plan(self, state):
        plan = MovementPlan(self.moves)

        sim = create_problem(
            self.player,
            state.map,
            self.moves,
        )

        while sim.step():
            pass

        actions = list(n for n in sim.var("actions").marking)
        for token in reversed(actions):
            step: MovementStep = token.value.action
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

    vis = Visualisation(create_problem(0, game_state.map, 20))
    vis.show()

    for _ in range(10):
        planner = MovementPlanner(player=0, moves=random.randint(1, 10))
        plan = planner.construct_plan(game_state)

        info(f"Constructed Attack Plan: {plan}, expected up to: {planner.moves}")
        for step in plan.steps:
            info(f"Step: {step}")

        input("Press Enter to continue...")
