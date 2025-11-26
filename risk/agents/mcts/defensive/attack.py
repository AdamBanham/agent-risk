from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.agents.plans import AttackPlan, AttackStep
from risk.utils.logging import debug, info
from risk.utils import map as mapping

from typing import Dict, Set, List
import random

from mcts.base.base import BaseState, BaseAction
from mcts.searcher.mcts import MCTS


class NoAttack(BaseAction):
    """
    An action for not attacking.
    """

    def __init__(self):
        super().__init__()

    def __eq__(self, other):
        return isinstance(other, NoAttack)

    def __hash__(self):
        return hash("noop")

    def __str__(self):
        return "no-atk"

    def __repr__(self):
        return str(self)


class Attack(BaseAction):
    """
    An action for attacking another territory.
    """

    def __init__(self, attacker: int, defender: int):
        super().__init__()
        self.attacker = attacker
        self.defender = defender

    def __eq__(self, other):
        if isinstance(other, Attack):
            return self.attacker == other.attacker and self.defender == other.defender
        return False

    def __hash__(self):
        return hash((self.attacker, self.defender))

    def __str__(self):
        return f"(A:{self.attacker})->(D:{self.defender})"

    def __repr__(self):
        return str(self)
    
    def to_step(self, state):
        map = state.map
        atk = map.get_node(self.attacker)
        deff = map.get_node(self.defender)
        return AttackStep(
            self.attacker, self.defender,
            max(deff.value + 5, deff.value * 3)
        )


class AttackState(BaseState):
    """
    State representing the attack phase.
    """

    def __init__(
        self,
        map: mapping.Graph,
        smap: mapping.SafeGraph,
        player: int,
        max_attacks: int,
        attacks: List[Attack] = None,
    ):
        self.player = player
        self.map = map.clone()
        self.smap: mapping.SafeGraph = smap.clone()
        self.max = max_attacks
        self.attacks: List[Attack] = []
        if attacks is not None:
            self.attacks.extend(attacks)

    def get_current_player(self) -> int:
        return 1  # Maximizer

    def get_possible_actions(self) -> List[Attack]:
        actions = []
        if len(self.attacks) < self.max:
            for terr in self.smap.frontline_nodes:
                for adj in self.map.get_adjacent_nodes(terr.id):
                    if adj.owner != terr.owner:
                        actions.append(Attack(terr.id, adj.id))
        actions.append(NoAttack())

        return actions

    def take_action(self, action: Attack) -> "AttackState":
        return AttackState(
            self.map, self.smap, self.player, self.max, self.attacks + [action]
        )

    def is_terminal(self) -> bool:
        return (
            len(self.attacks) >= self.max
            or len(
                [
                    f
                    for f in self.smap.frontline_nodes
                    if self.map.get_node(f.id).value > 1
                ]
            )
            == 0
            or (len(self.attacks) > 0 and isinstance(self.attacks[-1], NoAttack))
        )

    def get_reward(self):
        reward = 0

        for act in self.attacks:
            if isinstance(act, NoAttack):
                continue

            atk = self.map.get_node(act.attacker)
            deff = self.map.get_node(act.defender)

            if atk.owner != self.player or deff.owner == self.player:
                reward -= 1
            elif max(deff.value + 5, deff.value * 3) > atk.value:
                reward -= 1
            else:
                debug(f"found attacks :: {act}")
                reward += 10

        return reward


def extractStatistics(searcher, action) -> dict:
    """Return simple statistics for ``action`` from ``searcher``."""
    statistics = {}
    statistics["rootNumVisits"] = searcher.root.numVisits
    statistics["rootTotalReward"] = searcher.root.totalReward
    statistics["actionNumVisits"] = searcher.root.children[action].numVisits
    statistics["actionTotalReward"] = searcher.root.children[action].totalReward
    return statistics


class AttackPlanner(Planner):
    """A planner for attacking defensively in Risk."""

    def __init__(self, player_id: int, max_attacks: int):
        super().__init__()
        self.player = player_id
        self.max_attacks = max_attacks

    def construct_plan(self, state: GameState) -> AttackPlan:
        """Create a attack plan for the given player in the current state."""

        plan = AttackPlan(self.max_attacks)
        safe_map = mapping.construct_safe_view(state.map, self.player)
        max_runtime = 500  # milliseconds

        actions = []
        for _ in range(self.max_attacks):
            mcts_state = AttackState(
                state.map.clone(),
                safe_map.clone(),
                self.player,
                self.max_attacks,
            )
            mcts = MCTS(time_limit=max(10, max_runtime // self.max_attacks))
            action, reward = mcts.search(mcts_state, need_details=True)

            debug(extractStatistics(mcts, action))

            if isinstance(action, NoAttack):
                break

            actions.append(action)
            mcts_state = mcts_state.take_action(action)


        debug(f"Generated actions for attack plan: {actions}")

        # Convert actions to plan steps
        for action in actions:
            step = action.to_step(state)
            plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.logging import setLevel, info
    from logging import DEBUG
    import random

    setLevel(DEBUG)

    for _ in range(10):
        game_state = GameState.create_new_game(25, 2, 50)
        game_state.initialise()
        game_state.update_player_statistics()

        map = game_state.map
        smap = mapping.construct_safe_view(map, 0)

        front = smap.frontline_nodes[0]
        game_state.get_territory(front.id).armies += 20000
        game_state.update_player_statistics()

        planner = AttackPlanner(0, 3)
        plan = planner.construct_plan(game_state)

        info(f"Constructed Attack Plan: {plan}")
        for step in plan.steps:
            info(f"Step: {step}")
            atk = game_state.map.get_node(step.attacker)
            deff = game_state.map.get_node(step.defender)
            info(f"Atk: {atk} -> Def: {deff}")

        input("Press Enter to continue...")
