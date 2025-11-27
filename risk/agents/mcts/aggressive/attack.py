from risk.agents.plans import Planner
from risk.state.game_state import GameState
from risk.agents.plans import AttackPlan, AttackStep
from risk.utils.logging import debug, info
from risk.utils import map as mapping
from ..base import extractStatistics

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

    def __init__(
        self, attacker: int, defender: int, atk_troops: int = 0, def_troops: int = 0
    ):
        super().__init__()
        self.attacker = attacker
        self.defender = defender
        self.atk_troops = atk_troops
        self.def_troops = def_troops

    def safe(self):
        return max(self.def_troops + 5, self.def_troops * 3) < self.atk_troops

    def to_step(self):
        return AttackStep(self.attacker, self.defender, self.atk_troops)

    def __eq__(self, other):
        if isinstance(other, Attack):
            return self.attacker == other.attacker and self.defender == other.defender
        return False

    def __hash__(self):
        return hash((self.attacker, self.defender))

    def __str__(self):
        return f"(A:{self.attacker})[{self.atk_troops:04d}]->[{self.def_troops:04d}](D:{self.defender}) S:{self.safe()} "

    def __repr__(self):
        return str(self)


def sum_of_adjacents(node: mapping.SafeNode, map: mapping.Graph, player: int) -> int:
    total = 0
    armies = map.get_node(node.id).value
    for neighbor in map.get_adjacent_nodes(node.id):
        if neighbor.owner != player:
            total += armies / neighbor.value
    return total


class AttackState(BaseState):
    """
    State representing the attack phase.
    """

    def __init__(
        self,
        map: mapping.Graph,
        player: int,
        max_attacks: int,
        attacks: int = 0,
        attacker=None,
        troops: int = 0,
    ):
        self.player = player
        self.map = map.clone()
        self.max = max_attacks
        self.attacks = attacks
        self._terminal = False
        self.troops = troops
        self.attacker = attacker

    def _set_terminal(self):
        self._terminal = True

    def get_current_player(self) -> int:
        return 1  # Maximizer

    def get_possible_actions(self) -> List[Attack]:
        actions = []
        if self.attacks < self.max and self.attacker is not None and self.troops > 1:
            for adj in self.map.get_adjacent_nodes(self.attacker.id):
                if adj.owner != self.player:
                    action = Attack(
                        self.attacker.id, adj.id, self.troops - 1, adj.value
                    )
                    actions.append(action)
        if actions == []:
            actions.append(NoAttack())
        random.shuffle(actions)
        return actions

    def take_action(self, action: Attack) -> "AttackState":
        if isinstance(action, NoAttack):
            state = AttackState(
                self.map.clone(),
                self.player,
                self.max,
                self.attacks + 1,
            )
            state._set_terminal()
            return state

        new_map = self.map.clone()

        new_map.get_node(action.attacker).value -= action.atk_troops
        next_attacker = None
        if action.safe():
            new_map.get_node(action.defender).owner = self.player
            new_map.get_node(action.defender).value = max(1, action.atk_troops // 2)
            next_attacker = new_map.get_node(action.defender)
        elif random.uniform(0, 1) < 0.33:
            new_map.get_node(action.defender).owner = self.player
            new_map.get_node(action.defender).value = max(1, action.atk_troops // 2)
            next_attacker = new_map.get_node(action.defender)
        else:
            pass

        return AttackState(
            new_map,
            self.player,
            self.max,
            self.attacks + 1,
            attacker=next_attacker,
            troops=action.atk_troops // 2,
        )

    def is_terminal(self) -> bool:
        return self._terminal or self.attacker is None or self.troops < 2

    def get_reward(self):
        nodes = self.map.nodes_for_player(self.player)
        armies = sum(n.value for n in nodes)
        return len(nodes) * (1 / armies)


class AttackPlanner(Planner):
    """A planner for attacking defensively in Risk."""

    def __init__(self, player_id: int, max_attacks: int):
        super().__init__()
        self.player = player_id
        self.max_attacks = max_attacks

    def construct_plan(self, state: GameState) -> AttackPlan:
        """Create a attack plan for the given player in the current state."""

        plan = AttackPlan(self.max_attacks)
        map = state.map.clone()
        safe_map = mapping.construct_safe_view(state.map, self.player)
        max_runtime = 100  # milliseconds

        actions = []
        # work out initial attacking piviot
        fronts = set(state.map.get_node(f.id) for f in safe_map.frontline_nodes)
        terrs = [
            (terr, sum_of_adjacents(terr, map, self.player))
            for terr in fronts
        ]
        terrs = sorted(terrs, key=lambda x: x[1], reverse=True)
        attacker = terrs[0]
        if attacker[1] < 0.25:
            attacker = None
        else:
            attacker = attacker[0]
            troops = attacker.value

        mcts_state = AttackState(
            map,
            self.player,
            self.max_attacks,
            attacker=attacker,
            troops=troops,
        )

        for _ in range(self.max_attacks):
            if mcts_state.is_terminal():
                break

            mcts = MCTS(time_limit=max(10, max_runtime // self.max_attacks))
            action, reward = mcts.search(mcts_state, need_details=True)
            debug("Selected action: {}".format(action))
            debug(extractStatistics(mcts, action))

            if isinstance(action, NoAttack):
                break

            mcts_state = mcts_state.take_action(action)
            actions.append(action)

        debug(f"Generated actions for attack plan: {actions}")

        # Convert actions to plan steps
        for action in reversed(actions):
            step = action.to_step()
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
        game_state.get_territory(front.id).armies += 50
        game_state.update_player_statistics()
        debug(f"Select territory: {game_state.map.get_node(front.id)}")

        planner = AttackPlanner(0, 3)
        plan = planner.construct_plan(game_state)

        info(f"Constructed Attack Plan: {plan}")
        for step in plan.steps:
            info(f"Step: {step}")

        input("Press Enter to continue...")
