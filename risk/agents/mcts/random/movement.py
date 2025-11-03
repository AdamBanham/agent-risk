import random
from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan
from risk.utils.movement import (
    find_connected_frontline_territories,
    find_movement_sequence,
    find_safe_frontline_territories,
)
from risk.utils.logging import debug, info
from risk.agents.plans import MovementPlan, RouteMovementStep, MovementStep

from typing import List, Set, Dict
from copy import deepcopy

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS


class MovementAction(BaseAction):

    def __init__(
        self,
        from_territory_id: int,
        to_territory_id: int,
        num_armies: int,
        act: bool = True,
    ):
        self.from_territory_id = from_territory_id
        self.to_territory_id = to_territory_id
        self.num_armies = num_armies
        self.act = act

    def execute(self, state: "MovementState") -> "MovementState":
        if self.act:
            new_armies = deepcopy(state.armies)
            new_armies[self.from_territory_id] -= self.num_armies
            new_armies[self.to_territory_id] += self.num_armies
            return MovementState(
                state.terrs,
                state.connected,
                new_armies,
                state.moves - 1,
            )
        return MovementState(
            state.terrs,
            state.connected,
            state.armies,
            state.moves,
            acting=False,
        )

    def is_acting(self) -> bool:
        return self.act

    def to_step(self, game_state: GameState):
        if self.act:
            movements = find_movement_sequence(
                game_state.get_territory(self.from_territory_id),
                game_state.get_territory(self.to_territory_id),
                self.num_armies,
            )
            moves = []
            if movements is not None:
                for move in movements:
                    moves.append(MovementStep(move.src.id, move.tgt.id, move.amount))
            return RouteMovementStep(moves, self.num_armies)
        return None

    def __str__(self):
        return str(
            (self.from_territory_id, self.to_territory_id, self.num_armies, self.act)
        )

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, MovementAction):
            return (
                self.from_territory_id == other.from_territory_id
                and self.to_territory_id == other.to_territory_id
                and self.num_armies == other.num_armies
            )
        return False

    def __hash__(self):
        return hash((self.from_territory_id, self.to_territory_id, self.num_armies))


class MovementState(BaseState):
    """
    A state representing the movement phase for MCTS.
    """

    def __init__(
        self,
        terrs: Set[int],
        connected: Dict[int, Set[int]],
        armies: Dict[int, int],
        moves: int = 0,
        acting: bool = True,
    ):
        self.terrs = terrs
        self.armies = armies
        self.connected = connected
        self.acting = acting
        self.moves = moves
        self._actions = self._generate_actions()

    def _generate_actions(self) -> List[MovementAction]:
        actions = []
        if self.acting and self.moves > 0:
            for from_terr in self.terrs:
                for to_terr in self.connected[from_terr]:
                    max_movable = self.armies[from_terr] - 1
                    if max_movable > 0:
                        num_armies = max_movable
                        actions.append(
                            MovementAction(from_terr, to_terr, num_armies, act=True)
                        )
            # Add a no-op action to end movement phase
            actions.append(MovementAction(-1, -1, 0, act=False))
        return actions

    def get_current_player(self):
        return 1

    def get_possible_actions(self):
        return self._actions

    def take_action(self, action):
        return action.execute(self)

    def is_terminal(self):
        if not self.acting:
            return True
        if self.moves == 0:
            return True
        if len(self._actions) == 0:
            return True
        return False

    def get_reward(self):
        base = 1.0 / (1.0 + self.moves)
        jitter = 0.25 + random.random() * (base - 0.25)
        return base + jitter


def extractStatistics(searcher, action) -> dict:
    """Return simple statistics for ``action`` from ``searcher``."""
    statistics = {}
    statistics["rootNumVisits"] = searcher.root.numVisits
    statistics["rootTotalReward"] = searcher.root.totalReward
    statistics["actionNumVisits"] = searcher.root.children[action].numVisits
    statistics["actionTotalReward"] = searcher.root.children[action].totalReward
    return statistics


class RandomMovements(Planner):
    """
    A planner that creates random movement plans.
    """

    def __init__(self, moves: int = 1, player: int = 0):
        super().__init__()
        self.moves = moves
        self.player = player

    def construct_plan(self, state: GameState) -> Plan:
        # Implementation of random movement plan construction
        safes, frontlines = find_safe_frontline_territories(state, self.player)
        connections = dict(
            (
                terr.id,
                [
                    o.id
                    for o in find_connected_frontline_territories(
                        terr, frontlines, safes + frontlines
                    )
                ],
            )
            for terr in safes + frontlines
        )

        starting_state = MovementState(
            terrs=set(terr.id for terr in safes),
            connected=connections,
            armies=dict((terr.id, terr.armies) for terr in safes + frontlines),
            moves=self.moves,
            acting=True,
        )
        debug(f"Is starting state terminal? {starting_state.is_terminal()}")

        max_runtime = 50  # milliseconds
        plan = MovementPlan(self.moves)

        if starting_state.is_terminal():
            return plan

        mcts = MCTS(time_limit=max_runtime)
        action, reward = mcts.search(starting_state, need_details=True)

        debug(extractStatistics(mcts, action))

        # recursively extract actions
        seq_actions = []
        node = mcts.root.children[action]
        seq_actions.append(action)
        depth = 0
        debug(f"Depth {depth}: Selected Action: {action}")
        while len(node.children.values()) > 0:
            for child in node.children.values():
                debug(
                    f"Child: {child}, Total Reward: {child.totalReward}, Num Visits: {child.numVisits}"
                )
            action, node = max(node.children.items(), key=lambda n: n[1].totalReward)
            depth += 1
            debug(f"Depth {depth}: Selected Action: {action}")
            seq_actions.append(action)

        # Convert actions to plan steps
        for action in seq_actions:
            step = action.to_step(state)
            if step is not None:
                plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import INFO

    from risk.utils.replay import simulate_turns

    setLevel(INFO)

    state = GameState.create_new_game(50, 2, 250)
    state.initialise()
    state, _ = simulate_turns(state, 50)

    with open("mcts_movement.state", "w") as f:
        f.write(repr(state))

    planner = RandomMovements(moves=3, player=0)
    plan = planner.construct_plan(state)

    if len(plan.steps) == 0:
        print("No movement plan generated for player 0")
        print("trying the other player...")
        planner = RandomMovements(moves=3, player=1)
        plan = planner.construct_plan(state)

    print("****")
    print(f"Generated Movement Plan: {plan}")
    for step in plan.steps:
        print(step)
