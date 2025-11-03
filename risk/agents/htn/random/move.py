from risk.agents.htn import gtpyhop as ghop
from risk.state import plan
from risk.state.game_state import GameState, Territory
from risk.utils.logging import debug
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
    tgt: int = None
    src: int = None
    curr: int = None
###
def c_select_troops(dom):
    state: MovementState = dom.planning
    debug(f"Selecting troops from safe territory {state.safe} with {state.armies[state.safe]} armies")
    max_troops = state.armies[state.safe] - 1
    if max_troops > 0:
        state.troops = max_troops
        return dom


def c_create_route(dom):
    state: MovementState = dom.planning
    if state.safe is not None and state.front is not None and state.troops > 0:
        state.routes += 1
        state.armies[state.safe] -= state.troops
        state.armies[state.front] += state.troops
        state.ret = state.ret + [ (state.safe, state.front, state.troops) ]
        state.safe = None
        state.front = None
        state.troops = 0
        return dom
    
def c_set_safe(dom, safe: int):
    state: MovementState = dom.planning
    state.safe = safe
    return dom

def c_set_unsafe(dom, safe: int):
    state: MovementState = dom.planning
    state.safe = None
    state.safes = state.safes - {safe}
    return dom

def c_set_frontline(dom, frontline: int):
    state: MovementState = dom.planning
    state.front = frontline
    return dom

### actions
def select_troops(dom):
    state: MovementState = dom.planning
    debug(f"Selecting troops from safe territory {state.safe} with {state.armies[state.safe]} armies")
    max_troops = state.armies[state.safe] - 1
    if max_troops > 0:
        state.troops = max_troops
        return dom


def create_route(dom):
    state: MovementState = dom.planning
    if state.safe is not None and state.front is not None and state.troops > 0:
        state.routes += 1
        state.armies[state.safe] -= state.troops
        state.armies[state.front] += state.troops
        state.ret = state.ret + [ (state.safe, state.front, state.troops) ]
        state.safe = None
        state.front = None
        state.troops = 0
        return dom
    
def set_safe(dom, safe: int):
    state: MovementState = dom.planning
    state.safe = safe
    return dom

def set_unsafe(dom, safe: int):
    state: MovementState = dom.planning
    state.safe = None
    state.safes = state.safes - {safe}
    return dom

def set_frontline(dom, frontline: int):
    state: MovementState = dom.planning
    state.front = frontline
    return dom
    
### method-tasks: find moveable safes
def m_find_frontlines(dom):
    state: MovementState = dom.planning
    frontlines = state.connections[state.safe]
    if frontlines:
        front = frontlines.pop()
        return [('set_frontline', front), ('select_troops',), ('create_route',)]
    return [('find_safe',)]

def m_find_safe(dom):
    state: MovementState = dom.planning
    safes = state.safes.copy()
    if len(safes) > 0:
        safe = safes.pop()
        debug(f"Considering safe territory {safe} with {state.armies[safe]} armies")
        if state.armies[safe] > 1:
            return [('set_safe', safe), 
                    ("select_front",),]
        else:
            return [('set_unsafe', safe), ('find_safe',)]
    else:
        return False


### top level
def routing(dom, arg, moves):
    state: MovementState = dom.planning
    if state.safes and state.frontlines and state.routes < moves:          
        return [
            ("find_safe",),
            ("planning", arg, moves),
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
    ghop.declare_commands(c_set_frontline, c_select_troops, c_create_route)
    ghop.declare_commands(c_set_safe, c_set_unsafe)
    ghop.declare_actions(set_frontline, select_troops, create_route)
    ghop.declare_actions(set_safe, set_unsafe)
    ghop.declare_unigoal_methods("planning", routing, halt)
    ghop.declare_task_methods("find_safe", m_find_safe)
    ghop.declare_task_methods("select_front", m_find_frontlines)


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
        plan = MovementPlan(moves)
        res = ghop.run_lazy_lookahead(dom, [("planning", "routes", moves)])
        if res:
            # res = ghop.run_lazy_lookahead(dom, res, 100000)
            debug(f"result :: {res.planning.ret}")
            for safe, front, troops in res.planning.ret:
                debug(f"Moving {troops} troops from {safe} to {front}")
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
        player_terrs = game_state.get_territories_owned_by(0)
        seen.add(pick.id)

    plan = RandomMovements.construct_plan(
        player_id=0, moves=moves, game_state=game_state
    )

    for step in plan.steps:
        print(step)
    assert len(plan) <= moves

    print(f"Generated Movement Plan: {str(plan)}")
