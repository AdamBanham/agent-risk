from ...plans import (
    Planner, MovementPlan, RouteMovementStep, MovementStep
)
from risk.state import GameState
from risk.utils.replay import simulate_turns
from risk.utils.movement import (
    find_safe_frontline_territories,
    find_connected_frontline_territories,
    find_movement_sequence
)

from simpn.helpers import Place, Transition
from simpn.simulator import SimTokenValue, SimToken
from ..bases import ExpressiveSimProblem as SimProblem
from ..bases import GuardedTransition

from typing import Dict, Set


def create_simulator(
    max_moves: int,
    safe_terrs: Set[int],
    frontline_terrs: Set[int],
    connections: Dict[int, Set[int]],
    armies: Dict[int, int],
) -> SimProblem:

    problem = SimProblem()

    class Start(Place):
        model = problem
        name = "start"

    start = problem.var("start")
    start.put(SimTokenValue("start-1", moves=max_moves))

    class SafeTerritories(Place):
        model = problem
        name = "safes"

    safe_territories = problem.var("safes")
    for terr in safe_terrs:
        if armies[terr] > 1:
            safe_territories.put(
                SimTokenValue(
                    f"safe-terr-{terr}",
                    territory=terr,
                    connections=connections[terr],
                    armies=armies[terr],
                )
            )

    class FrontlineTerritories(Place):
        model = problem
        name = "frontline"

    frontline_territories = problem.var("frontline")
    for terr in frontline_terrs:
        frontline_territories.put(
            SimTokenValue(f"frontline-terr-{terr}", territory=terr)
        )

    class Actions(Place):
        model = problem
        name = "actions"

    class Viable(Place):
        model = problem
        name = "viable"

    class Invalid(Place):
        model = problem
        name = "invalid"

    class Complete(Place):
        model = problem
        name = "complete"

    def check_for_viable() -> bool:
        return len(safe_territories.marking) > 0

    class InitatePlan(Transition):
        model = problem
        name = "initiate-plan"
        incoming = ["start"]
        outgoing = ["planning", "viable", "invalid"]

        def behaviour(tok_val: SimTokenValue):
            viable = None
            invalid = None
            if check_for_viable():
                viable = SimTokenValue("viable")
            else:
                invalid = SimTokenValue("invalid")
            return [
                SimToken(tok_val),
                SimToken(viable) if viable else None,
                SimToken(invalid) if invalid else None,
            ]

    class CompletePlan(GuardedTransition):
        model = problem
        name = "complete-plan"
        incoming = ["planning"]
        outgoing = ["complete"]

        def guard(tok_val: SimTokenValue):
            if tok_val.moves == 0:
                return True
            return False

        def behaviour(tok_val: SimTokenValue):
            return [SimToken(tok_val)]

    class ClosePlan(Transition):
        model = problem
        incoming = ["planning", "invalid"]
        outgoing = ["complete"]
        name = "close-plan"

        def behaviour(
            tok_val: SimTokenValue,
            invalid_val: SimTokenValue,
        ):
            return [SimToken(tok_val)]

    class GenerateMovement(GuardedTransition):
        model = problem
        name = "generate-movement"
        incoming = ["planning", "safes", "frontline", "viable"]
        outgoing = ["check", "safes", "frontline", "actions"]

        def guard(
            tok_val: SimTokenValue,
            safe_val: SimTokenValue,
            frontline_val: SimTokenValue,
            viable_val: SimTokenValue,
        ):
            if tok_val.moves > 0:
                if frontline_val.territory in safe_val.connections:
                    return True
            return False

        def behaviour(
            tok_val: SimTokenValue,
            safe_val: SimTokenValue,
            frontline_val: SimTokenValue,
            viable_val: SimTokenValue,
        ):
            new_val = tok_val.clone()
            new_val.moves -= 1
            pick = safe_val.armies - 1
            action_val = SimTokenValue(
                f"move-from-{safe_val.territory}-to-{frontline_val.territory}",
                from_terr=safe_val.territory,
                to_terr=frontline_val.territory,
                troops=pick,
            )
            new_safe_val = safe_val.clone()
            new_safe_val.armies -= pick

            return [
                SimToken(new_val),
                SimToken(new_safe_val) if new_safe_val.armies > 1 else None,
                SimToken(frontline_val),
                SimToken(action_val),
            ]

    class Check(Transition):
        model = problem
        name = "checking"
        incoming = ["check"]
        outgoing = ["planning", "viable", "invalid"]

        def behaviour(
            tok_val: SimTokenValue,
        ):
            viable = None
            invalid = None
            if check_for_viable():
                viable = SimTokenValue("viable")
            else:
                invalid = SimTokenValue("invalid")
            return [
                SimToken(tok_val),
                SimToken(viable) if viable else None,
                SimToken(invalid) if invalid else None,
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
        
        terrs = state.get_territories_owned_by(self.player_id)
        safes, frontlines = find_safe_frontline_territories(state, self.player_id)

        sim = create_simulator(
            self.max_moves,
            safe_terrs=set(t.id for t in safes),
            frontline_terrs=set(t.id for t in frontlines),
            connections=dict(
                (
                    s.id,
                    set(
                        o.id
                        for o in find_connected_frontline_territories(
                            s, frontlines, safes + frontlines
                        )
                    ),
                )
                for s in safes
            ),
            armies=dict(
                (t.id, t.armies) for t in terrs
            ),
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
    state = GameState.create_new_game(52, 2, 50)
    state.initialise()
    state.update_player_statistics()

    state, _ = simulate_turns(state, 100)

    terrs = state.get_territories_owned_by(0)
    safes, frontlines = find_safe_frontline_territories(state, 0)

    sim = create_simulator(
        1,
        safe_terrs=set(t.id for t in safes),
        frontline_terrs=set(t.id for t in frontlines),
        connections=dict(
            (
                s.id,
                set(
                    o.id
                    for o in find_connected_frontline_territories(
                        s, frontlines, safes + frontlines
                    )
                ),
            )
            for s in safes
        ),
        armies=dict(
            (t.id, t.armies) for t in terrs
        ),
    )

    from simpn.visualisation import Visualisation

    vis = Visualisation(sim)
    vis.show()
