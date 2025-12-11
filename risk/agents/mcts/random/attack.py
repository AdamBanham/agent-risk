from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.state.plan import Plan
from risk.agents.plans import AttackPlan, AttackStep
from risk.utils.logging import debug
from risk.utils import map as mapping

from typing import Set, List, Collection
import random

from mcts.base.base import BaseState
from mcts.searcher.mcts import MCTS
from ..base import NoAction, BaseAgentAction
from ..base import extractStatistics


class NoAttack(NoAction):
    """
    Noop for attacking.
    """

    def __init__(self):
        super().__init__()

    def execute(self, state: "AttackState"):
        return AttackState(
            state.attacks, state.terrs, state.map, state._actions + [self]
        )


class AttackAction(BaseAgentAction):
    """
    Action for attacking.
    """

    def __init__(
        self,
        attacker: int,
        defender: int,
        num_attackers: int,
    ):
        super().__init__(False)
        self.attacker = attacker
        self.defender = defender
        self.num_attackers = num_attackers

    def to_step(self):
        return AttackStep(self.attacker, self.defender, self.num_attackers)

    def execute(self, state: "AttackState") -> "AttackState":
        return AttackState(
            state.attacks - 1,
            state.terrs.difference(set([self.attacker])),
            state.map,
            state._actions + [self],
        )

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
        return hash((self.id, self.attacker, self.defender, self.num_attackers))


class AttackState(BaseState):

    def __init__(
        self,
        attacks: int,
        terrs: Set[int],
        map: mapping.Graph,
        actions: Collection[BaseAgentAction] = None,
    ):
        super().__init__()
        self.attacks = attacks
        self.terrs = terrs
        self.map = map.clone()
        self._actions = [a for a in actions] if actions else []

    def get_current_player(self):
        return 1  # Maximise

    def get_possible_actions(self) -> List[AttackAction]:
        options = []

        if self.attacks == 0:
            options.append(NoAttack())
        else:
            # for each terr, add an attack on enemy adjacent
            for terr in self.terrs:
                node = self.map.get_node(terr)
                for adj in self.map.get_adjacent_nodes(terr):
                    if adj.owner != node.owner:
                        troops = node.value - 1
                        if troops > 1:
                            troops = random.randint(1, troops)

                        options.append(AttackAction(node.id, adj.id, troops))
        if not options:
            options.append(NoAttack())
        random.shuffle(options)
        return options

    def take_action(self, action: AttackAction) -> "AttackState":
        return action.execute(self)

    def is_terminal(self) -> bool:
        if len(self._actions) > 0:
            last = self._actions[-1]
            return last.is_terminal()
        return False

    def get_reward(self) -> float:
        return len(self._actions[:-1])


class RandomAttacks(Planner):
    """
    A planner that creates random attack plans.
    """

    def __init__(
        self, player: int = 0, pos_attacks: int = 0, attack_probability: float = 0.5
    ):
        super().__init__()
        self.player = player
        self.pos_attacks = pos_attacks
        self.attack_probability = attack_probability

    def construct_plan(self, state: GameState) -> Plan:
        # flip for the number of attacks
        max_runtime = 100  # milliseconds
        num_attacks = 0
        pick = random.uniform(0, 1)
        while pick <= self.attack_probability and num_attacks < self.pos_attacks:
            num_attacks += 1
            pick = random.uniform(0, 1)

        # pick a frontline territory with more than one troop
        map = state.map
        safe_map = mapping.construct_safe_view(map, self.player)
        terrs = set(
            n.id for n in safe_map.frontline_nodes if map.get_node(n.id).value > 2
        )

        plan = AttackPlan(num_attacks)
        actions = []
        mcts_state = AttackState(num_attacks, terrs, map)

        if num_attacks == 0:
            return plan

        for i in range(num_attacks + 1):
            if mcts_state.is_terminal():
                break
            debug(f"starting mcts for attacking {i+1}/{num_attacks+1}...")
            mcts = MCTS(time_limit=max(10, max_runtime // num_attacks + 1))
            action, reward = mcts.search(mcts_state, need_details=True)
            actions.append(action)
            mcts_state = mcts_state.take_action(action)
            debug(f"mcts finished, taking {action} with expected reward of {reward}")
            debug(extractStatistics(mcts, action))

        debug(f"Generated actions for attacks plan: {actions}")

        # Convert actions to plan steps
        for action in actions:
            step = action.to_step()
            if step:
                plan.add_step(step)
        return plan


if __name__ == "__main__":
    from risk.state.game_state import GameState
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(25, 2, 50)
    state.initialise()
    state.update_player_statistics()

    map = state.map

    for _ in range(10):
        player = random.randint(0, 1)
        planner = RandomAttacks(player, 5, 0.7)
        plan = planner.construct_plan(state)

        debug(f"Constructed Plan: {plan}")
        assert len(plan.steps) <= 5, "Expected no more than 5 attacks"
        seen = set()
        for step in plan.steps:
            debug(step)

            atk_node = map.get_node(step.attacker)
            def_node = map.get_node(step.defender)
            troops = step.troops
            assert atk_node.id not in seen, "Expected only one attack from each terr"
            assert atk_node.owner == player, "Expected attacker to belong to player"
            assert def_node.owner != player, "Expected defender to not belong to player"
            assert (
                troops > 0 and troops < atk_node.value
            ), "Expected troops to higher than 0 and less than value of attacker"

            seen.add(atk_node.id)

        input("continue?")
