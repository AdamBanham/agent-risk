from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan
from risk.agents.plans import AttackPlan, AttackStep
from risk.utils.logging import debug, info
from risk.utils.movement import find_safe_frontline_territories

from typing import Dict, Set, List
import random

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS


class AttackAction(BaseAction):

    def __init__(
        self,
        attacker: int,
        defender: int,
        num_attackers: int,
        act: bool = True,
    ):
        super().__init__()
        self.attacker = attacker
        self.defender = defender
        self.num_attackers = num_attackers
        self.act = act

    def is_acting(self) -> bool:
        return self.act

    def to_step(self):
        if self.act:
            return AttackStep(self.attacker, self.defender, self.num_attackers)
        return None

    def execute(self, state: "AttackState") -> "AttackState":
        if self.act:
            new_armies = state.armies.copy()
            new_armies[self.attacker] -= self.num_attackers
            return AttackState(
                state.terrs,
                new_armies,
                attacks=state.attacks - 1,
            )
        else:
            return AttackState(state.terrs, state.armies, acting=False)

    def __str__(self):
        return str((self.attacker, self.defender, self.num_attackers))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, AttackAction):
            return (
                self.attacker == other.attacker
                and self.defender == other.defender
                and self.num_attackers == other.num_attackers
            )
        return False

    def __hash__(self):
        return hash((self.attacker, self.defender, self.num_attackers))


class AttackState(BaseState):

    def __init__(
        self,
        terrs: Dict[int, Set[int]],
        armies: Dict[int, int],
        acting: bool = True,
        attacks: int = 0,
    ):
        super().__init__()
        self.terrs = terrs
        self.armies = armies
        self.acting = acting
        self.attacks = attacks

    def is_acting(self) -> bool:
        return self.acting

    def _generate_actions(self) -> List[AttackAction]:
        actions = []
        if self.acting:
            for attacker in self.terrs:
                for defender in self.terrs[attacker]:
                    max_attackers = self.armies[attacker] - 1
                    if max_attackers > 0:
                        num_attackers = max_attackers
                        for attacking in range(1, num_attackers + 1):
                            actions.append(
                                AttackAction(attacker, defender, attacking, act=True)
                            )
            # Add a no-op action to end attack phase
            actions.append(AttackAction(-1, -1, 0, act=False))
            random.shuffle(actions)
        return actions

    def get_current_player(self):
        return 1

    def get_possible_actions(self) -> List[AttackAction]:
        return self._generate_actions()

    def take_action(self, action: AttackAction) -> "AttackState":
        return action.execute(self)

    def is_terminal(self) -> bool:
        return not self.acting or len(self.get_possible_actions()) == 0 or self.attacks <= 0

    def get_reward(self) -> float:
        base = 1.0 / (1.0 + self.attacks)
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

class RandomAttacks(Planner):
    """
    A planner that creates random attack plans.
    """

    def __init__(
        self, pos_attacks: int = 0, player: int = 0, attack_probability: float = 0.5
    ):
        super().__init__()
        self.pos_attacks = pos_attacks
        self.player = player
        self.attack_probability = attack_probability

    def construct_plan(self, state: GameState) -> Plan:
        # flip for the number of attacks 
        num_attacks = 1
        pick = random.uniform(0, 1)
        while pick <= self.attack_probability:
            num_attacks += 1
            pick = random.uniform(0, 1)

        owned_terrs = state.get_territories_owned_by(self.player)
        terrs = dict(
            (terr.id, set(adj.id for adj in terr.adjacent_territories))
            for terr in owned_terrs
        )
        plan = AttackPlan(self.pos_attacks) 
        
        starting_state = AttackState(
            terrs=terrs,
            armies={terr.id: terr.armies for terr in owned_terrs},
            attacks=num_attacks,
            acting=True,
        )

        debug(f"Is starting state terminal? {starting_state.is_terminal()}")
        max_runtime = 15  # milliseconds

        if starting_state.is_terminal():
            return plan
        seq_actions = []

        for attack in range(num_attacks):
            debug(f"Starting MCTS for attack {attack + 1}/{num_attacks}")

            if starting_state.is_terminal():
                debug("Reached terminal state, ending attack planning.")
                break

            mcts = MCTS(time_limit=max_runtime)
            action, reward = mcts.search(starting_state, need_details=True)
            seq_actions.append(action)

            debug(extractStatistics(mcts, action))
            starting_state = starting_state.take_action(action)

        # Convert actions to plan steps
        debug(f"Constructed sequence of actions: {seq_actions}")
        for action in seq_actions:
            step = action.to_step()
            if step is not None:
                plan.add_step(step)
        return plan
    

if __name__ == "__main__":
    from risk.state.game_state import GameState
    from risk.utils.logging import setLevel
    from logging import INFO, DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(50, 2, 150)
    state.initialise()

    planner = RandomAttacks(3, 1, 0.7)
    plan = planner.construct_plan(state)

    info(f"Constructed Plan: {plan}")
    for step in plan.steps:
        print(step)