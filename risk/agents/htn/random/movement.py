from risk.agents.htn import gtpyhop as ghop
from risk.state import plan
from risk.state.game_state import GameState, Territory
from ..bases import HTNStateWithPlan
from ...plans import MovementPlan, RouteMovementStep, MovementStep
from ....utils.movement import (
    find_safe_frontline_territories,
    find_movement_sequence,
    find_connected_frontline_territories,
)

from typing import Dict, Dict, Set
from dataclasses import dataclass, field
import random


@dataclass
class MovementState(HTNStateWithPlan):
    safes: Set[int] = field(default_factory=set)
    frontlines: Set[int] = field(default_factory=set)
    connections: Dict[int, Set[int]] = field(default_factory=dict)
    armies: Dict[int, int] = field(default_factory=dict)
    ret: list = field(default_factory=list)
    moves: int = 0
    routes: int = 0
    safe: int = None
    front: int = None
    troops: int = 0


### actions
def select_front(dom, safe: int, frontlines: Set[int] = None):
    state: MovementState = dom.planning
    if frontlines:
        state.safe = safe
        possible_fronts = [
            f for f in frontlines if f in state.connections[state.safe]
        ]
        if possible_fronts:
            state.front = random.choice(possible_fronts)
            return dom
        else:
            return [("planning", "routes", state.routes)]


def select_troops(dom, safe: int, armies: int):
    state: MovementState = dom.planning
    max_troops = armies - 1
    if max_troops > 0:
        state.troops = max_troops
        return dom


def create_route(dom, ret):
    state: MovementState = dom.planning
    if state.safe and state.front:
        state.routes += 1
        state.armies[state.safe] -= state.troops
        state.armies[state.front] += state.troops
        ret.append((state.safe, state.front, state.troops))
        dom.planning.ret = ret
        return dom


### methods
def routing(dom, arg, moves):
    state: MovementState = dom.planning
    if state.safes and state.frontlines and state.routes < moves:
        movable_safes = [
            t for t in state.safes if state.armies[t] > 1
        ]
        if not movable_safes:
            return False
        else:
            safe_pick = random.choice(movable_safes)

            if state.armies[safe_pick] <= 1:
                state.safes = state.safes - {safe_pick}
                return [
                    ("planning", "routes", moves)
                ]

            state.safes = state.safes - {safe_pick}            

            if len(state.connections[safe_pick]) > 0:
                return [
                    # ("select_safe", movable_safes),
                    ("select_front", safe_pick, state.connections[safe_pick]),
                    ("select_troops", safe_pick, state.armies[safe_pick]),
                    ("create_route", state.ret),
                    ("planning", arg, moves),
                ]
            else:
                return [
                    ("planning", "routes", moves)
                ]
    else:
        return False


def halt(dom, arg, moves):
    state: MovementState = dom.planning
    if state.routes == moves:
        return True
    else:
        return False


### helpers


def create_state(player: int, moves: int, game_state: GameState) -> object:

    safe, frontline = find_safe_frontline_territories(game_state, player)
    terrs = safe + frontline
    connections = {
        t.id: set(
            o.id for o in find_connected_frontline_territories(t, frontline, terrs)
        )
        for t in safe
    }
    terrs = dict((t.id, t) for t in terrs)
    armies = {t.id: t.armies for t in terrs.values()}

    dom = ghop.State(
        "movements",
        **{
            "planning": MovementState(
                player=player,
                moves=moves,
                safes=set(t.id for t in safe),
                frontlines=set(t.id for t in frontline),
                connections=connections,
                plan=MovementPlan(moves),
                armies=armies,
                routes=0,
            )
        },
    )

    return dom


def create_planner():
    ghop.current_domain = ghop.Domain("htn_random_movement")
    ghop.declare_actions(select_front, select_troops, create_route)
    ghop.declare_unigoal_methods("planning", routing, halt)


class RandomMovements:
    """
    Finds a random route from a safe territory to a frontline
    territory.
    """

    def __init__(self):
        pass

    @staticmethod
    def construct_plan(
        player_id: int,
        moves: int,
        game_state: GameState,
    ) -> MovementPlan:

        create_planner()
        dom = create_state(player_id, moves, game_state)

        res = ghop.pyhop(dom, [("planning", "routes", moves)])
        print(f"result :: {res}")
        plan:MovementPlan = dom.planning.plan
        for safe, front, troops in dom.planning.ret:
            print(f"Moving {troops} troops from {safe} to {front}")
            movements = find_movement_sequence(
                        game_state.get_territory(safe), 
                        game_state.get_territory(front), 
                        troops
            )
            movements = [
                MovementStep(step.src.id, step.tgt.id, step.amount) for step in movements
            ]
            plan.add_step(
                RouteMovementStep(
                    movements, troops
                )
            )

        return plan


if __name__ == "__main__":

    ghop.verbose = 4

    game_state = GameState.create_new_game(100, 2, 500)
    game_state.initialise()

    moves = 3

    player_terrs = game_state.get_territories_owned_by(0)
    seen = set()
    for _ in range(moves):
        pick = random.choice(player_terrs)
        while pick.id in seen:
            pick = random.choice(player_terrs)
        pick.add_armies(5)
        for adj in pick.adjacent_territories:
            if adj.owner != 0:
                adj.set_owner(0, 2)
        game_state.update_player_statistics()
        seen.add(pick.id)

    plan = RandomMovements.construct_plan(
        player_id=0, moves=moves, game_state=game_state
    )

    for step in plan.steps:
        print(step)
    assert len(plan) <= moves

    print(f"Generated Movement Plan: {str(plan)}")
