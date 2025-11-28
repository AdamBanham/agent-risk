from ...plans import Planner, MovementStep, RouteMovementStep, MovementPlan
from ..bases import GuardedTransition, ExpressiveSimProblem
from risk.utils import map as mapping
from risk.utils.movement import find_movement_sequence

import random

from simpn.helpers import Place
from simpn.simulator import SimToken, SimTokenValue


def sum_of_adjacents(node: mapping.SafeNode, map: mapping.Graph, player) -> int:
    total = 0
    for neighbor in map.get_adjacent_nodes(node.id):
        if neighbor.owner != player:
            total += (1.0 / neighbor.value) * 10
    return total


def create_problem(player: int, map: mapping.Graph, moves: int) -> ExpressiveSimProblem:
    """
    Constructs a SimProblem for deciding moves.
    """

    problem = ExpressiveSimProblem()
    network_map = mapping.construct_network_view(map, player)

    def finder(node: mapping.SafeNode) -> float:
        return sum_of_adjacents(node, map, player)

    targets = {}
    for network in network_map.networks:
        view = network_map.view(network)
        armies = sum(map.get_node(t.id).value for t in view.nodes)
        movable = armies - view.size
        fronts = view.frontlines_in_network(network)
        weights = [finder(front) for front in fronts]

        top_most = random.randint(1, min(3, len(fronts)))
        options = sorted(
            zip(fronts, weights),
            key=lambda x: x[1],
            reverse=True,
        )[:top_most]

        total_weight = sum(w for f, w in options)
        for front, weight in options:
            targets[front.id] = max(1, int((weight / total_weight) * movable))

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
                moving = min(src.armies - 1, targets.get(tgt.id, 1) - tgt.armies)
            else:
                moving = min(
                    src.armies - targets.get(src.identify, 1),
                    targets.get(tgt.id, 1) - tgt.armies,
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
            target = targets.get(terr.id, 1)
            if terr.armies < target:
                if other.network == terr.network and terr.id != other.identify:
                    if other.armies > 1:
                        if other.safe or other.armies > targets.get(other.identify, 1):
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

            route = find_movement_sequence(
                state.get_territory(step.source),
                state.get_territory(step.destination),
                step.troops,
            )

            step = RouteMovementStep(
                [MovementStep(move.src.id, move.tgt.id, move.amount) for move in route],
                step.troops,
            )

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
