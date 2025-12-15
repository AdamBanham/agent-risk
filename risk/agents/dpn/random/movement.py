from ...plans import (
    Planner, MovementPlan, RouteMovementStep, MovementStep
)
from risk.state import GameState
from risk.utils import map as mapping
from risk.utils.logging import debug
from risk.utils.movement import (
    find_movement_sequence
)

import random

from simpn.helpers import Place
from simpn.simulator import SimTokenValue, SimToken
from ..bases import ExpressiveSimProblem as SimProblem
from ..bases import GuardedTransition

def priority(bindings):
    debug(f"Num of bindings: {len(bindings)}")
    bindings = list(bindings)
    random.shuffle(bindings)
    return random.choice(bindings)


def create_simulator(
    map: mapping.Graph,
    network_map: mapping.NetworkGraph,
    max_moves: int,
) -> SimProblem:

    problem = SimProblem(
        binding_priority=priority
    )

    class Start(Place):
        model = problem
        name = "start"
        amount = max_moves

    class Safes(Place):
        model = problem
        name = "safes"

    safes = problem.var("safes")
    for network in network_map.networks:
        for fnode in network_map.safes_in_network(network):
            safes.put(
                SimTokenValue(
                    f"safe-terr-{fnode.id}",
                    territory=fnode.id,
                    network=network,
                    armies=mapping.get_value(map, fnode.id),
                )
            )

    class Frontlines(Place):
        model = problem
        name = "frontlines"

    fronts = problem.var("frontlines")
    for network in network_map.networks:
        for fnode in network_map.frontlines_in_network(network):
            fronts.put(
                SimTokenValue(
                    f"frontline-terr-{fnode.id}",
                    territory=fnode.id,
                    network=network,
                    armies=mapping.get_value(map, fnode.id),
                )
            )

    class GenerateMovement(GuardedTransition):
        model = problem
        name = "generate-movement"
        incoming = ["start", "safes", "frontlines",]
        outgoing = ["actions", "safes", "frontlines",]

        def guard(
            tok_val: SimTokenValue,
            safe_val: SimTokenValue,
            frontline_val: SimTokenValue,
        ):
            if safe_val.network == frontline_val.network and safe_val.armies >= 2:
                return True
            return False

        def behaviour(
            tok_val: SimTokenValue,
            safe_val: SimTokenValue,
            frontline_val: SimTokenValue,
        ):
            pick = safe_val.armies - 1
            action_val = SimTokenValue(
                f"move-from-{safe_val.territory}-to-{frontline_val.territory}",
                from_terr=safe_val.territory,
                to_terr=frontline_val.territory,
                troops=pick,
            )
            new_safe_val = safe_val.clone()
            new_safe_val.armies -= pick

            new_frontline_val = frontline_val.clone()
            new_frontline_val.armies += pick

            return [
                SimToken(action_val),
                SimToken(new_safe_val) if new_safe_val.armies > 1 else None,
                SimToken(frontline_val),
            ]

    return problem


class RandomMovement(Planner):
    """
    A planner that generates random routes between safe and
    frontline territories for movement plans.
    """

    def __init__(self, player_id: int, max_moves: int):
        super().__init__()
        self.player_id = player_id
        self.max_moves = max_moves

    def construct_plan(self, state: GameState) -> MovementPlan:
        # Placeholder logic for random movement plan generation
        plan = MovementPlan(self.max_moves)
        
        sim = create_simulator(
            state.map.clone(),
            mapping.construct_network_view(state.map, self.player_id),
            self.max_moves,
        )

        while sim.step():
            pass

        for tok in sim.var("actions").marking:
            val:SimTokenValue = tok.value
            movement = find_movement_sequence(
                state.get_territory(val.from_terr),
                state.get_territory(val.to_terr),
                val.troops
            )
            movement = [
                MovementStep(
                    source=move.src.id,
                    destination=move.tgt.id,
                    troops=move.amount
                )
                for move 
                in movement
            ]
            step = RouteMovementStep(
                movement, val.troops
            )
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG
    setLevel(DEBUG)

    state = GameState.create_new_game(52, 2, 250)
    state.initialise()
    state.update_player_statistics()

    sim = create_simulator(
        state.map.clone(),
        mapping.construct_network_view(state.map, 0),
        2
    )

    from simpn.visualisation import Visualisation

    vis = Visualisation(sim)
    vis.show()

    planner = RandomMovement(player_id=0, max_moves=2)
    plan = planner.construct_plan(state)

    debug(plan)
    assert len(plan.steps) <= 2, "Expected at most 2 movement steps, got {}".format(len(plan.steps))
    for step in plan.steps:
        debug(step)

