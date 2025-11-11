from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import find_movement_sequence, Movement
from risk.utils.movement import find_safe_frontline_territories
from risk.utils.movement import find_connected_frontline_territories

from typing import Set, Dict
import random

from simpn.helpers import BPMN
from simpn.simulator import SimTokenValue, SimToken
from .base import ExpressiveSimProblem as SimProblem


def construct_simulator(
    safes: Set[int],
    frontlines: Set[int],
    armies: Dict[int, int],
    connections: Dict[int, Set[int]],
    max_moves: int,
):
    problem = SimProblem()

    class Start(BPMN):
        model = problem
        type = "resource-pool"
        name = "planning-started"
        amount = 1

    class Finish(BPMN):
        model = problem
        type = "end"
        name = "finished"
        incoming = ["finish"]

    class Planner(BPMN):
        model = problem
        name = "planner"
        type = "resource-pool"
        amount = 0

    planner = problem.var("planner")
    planner.set_invisible_edges()
    move_tok = SimTokenValue(
        "move",
        safes=safes,
        frontlines=frontlines,
        armies=armies,
        connections=connections,
        moves_left=max_moves,
        actions=[],
    )
    planner.put(move_tok)

    class Rejoin(BPMN):
        model = problem
        type = "gat-ex-join"
        name = "rejoining"
        incoming = ["planning-started", "rejoin"]
        outgoing = ["checking"]

    class MoveCheck(BPMN):
        model = problem
        type = "task"
        name = "check for moves"
        incoming = ["checking", "planner"]
        outgoing = ["checked", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()
            new_planner.moving = new_planner.moves_left > 0

            can_move = False
            remove = set()
            for terr in new_planner.safes:
                if new_planner.armies[terr] > 1:
                    can_move = True
                else:
                    remove.add(terr)
            new_planner.safes -= remove

            new_planner.moving = new_planner.moving and can_move

            if not isinstance(tok_val, SimTokenValue):
                new_tok_val = SimTokenValue(
                    tok_val,
                    moving=new_planner.moving,
                )
            else:
                new_tok_val = tok_val.clone()
                new_tok_val.moving = new_planner.moving

            return [SimToken((new_tok_val, new_planner))]

    class MoveSplit(BPMN):
        model = problem
        type = "gat-ex-split"
        name = "decide to move"
        incoming = [
            "checked",
        ]
        outgoing = [
            "moving",
            "finish",
        ]

        def choice(tok_val: SimTokenValue):
            if tok_val.moving:
                return [
                    SimToken(tok_val),
                    None,
                ]
            else:
                return [
                    None,
                    SimToken(tok_val),
                ]

    class SelectMove(BPMN):
        model = problem
        type = "task"
        name = "select move"
        incoming = ["moving", "planner"]
        outgoing = ["selected", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()

            src = random.choice(list(new_planner.safes))
            tgt = random.choice(list(new_planner.connections[src]))
            amount = planner.armies[src] - 1

            new_planner.selected = {
                "from": src,
                "to": tgt,
                "amount": amount,
            }

            return [SimToken((tok_val, new_planner))]

    class ExecuteMove(BPMN):
        model = problem
        type = "task"
        name = "execute move"
        incoming = ["selected", "planner"]
        outgoing = ["rejoin", "planner"]

        def behaviour(tok_val, planner: SimTokenValue):
            new_planner = planner.clone()
            new_planner.moves_left -= 1
            # Execute one random move
            # Update armies and moves_left accordingly
            new_planner.actions.append(
                Movement(
                    src=new_planner.selected["from"],
                    tgt=new_planner.selected["to"],
                    amount=new_planner.selected["amount"],
                )
            )
            new_planner.armies[new_planner.selected["from"]] -= new_planner.selected[
                "amount"
            ]
            new_planner.armies[new_planner.selected["to"]] += new_planner.selected[
                "amount"
            ]

            return [SimToken((tok_val, new_planner))]

    return problem


class RandomMovement(Planner):
    """
    A planner that generates random movement plans.
    """

    def __init__(self, player_id: int, max_moves: int):
        super().__init__()
        self.player_id = player_id
        self.max_moves = max_moves

    def construct_plan(self, game_state: GameState) -> MovementPlan:
        # Implementation of random movement plan generation
        safes, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )
        safes_ids = set(t.id for t in safes)
        frontlines_ids = set(t.id for t in frontlines)
        connections = dict(
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
        )

        sim = construct_simulator(
            safes=safes_ids,
            frontlines=frontlines_ids,
            armies={t.id: t.armies for t in safes + frontlines},
            connections=connections,
            max_moves=self.max_moves,
        )

        while sim.step():
            pass

        plan = MovementPlan(self.max_moves)
        planner = sim.var("planner").marking[0]

        for movement in planner.value.actions:
            move_seq = find_movement_sequence(
                src=game_state.get_territory(movement.src),
                tgt=game_state.get_territory(movement.tgt),
                amount=movement.amount,
            )
            step = RouteMovementStep(
                [
                    MovementStep(move.src.id, move.tgt.id, move.amount)
                    for move in move_seq
                ],
                movement.amount,
            )
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from os.path import exists, join

    layout_file = join(".", "bpmn_random_movement.layout")
    sim = construct_simulator(
        safes={1, 2, 3},
        frontlines={4, 5, 6},
        armies={1: 5, 2: 3, 3: 2, 4: 4, 5: 6, 6: 1},
        connections={
            1: {4, 5},
            2: {5},
            3: {6},
            4: {1, 5},
            5: {1, 2, 4, 6},
            6: {3, 5},
        },
        max_moves=1,
    )

    from simpn.visualisation import Visualisation

    if exists(layout_file):
        vis = Visualisation(sim, layout_file=layout_file)
    else:
        vis = Visualisation(sim)
    vis.show()
    vis.save_layout(layout_file)
