from risk.agents.htn import gtpyhop as ghop
from risk.state.game_state import GameState
from ..bases import HTNStateWithPlan
from ...plans import AttackPlan, AttackStep

from typing import Dict, Dict, Set
from dataclasses import dataclass, field
import random


@dataclass
class AttackState(HTNStateWithPlan):
    territories: Set[int] = field(default_factory=set)
    armies: Dict[int, int] = field(default_factory=dict)
    attacks: int = 0
    terr: int = None
    adjacents: Dict[int, Set[int]] = field(default_factory=dict)
    adjacent: int = None
    troops: int = 0


def select_terr(dom, territories: Set[int] = None):
    state: AttackState = dom.attacking
    if territories:
        state.terr = random.choice(list(territories))
        return dom


def select_adj(dom, adjacents: Dict[int, Set[int]] = None):
    state: AttackState = dom.attacking
    if adjacents:
        state.adjacent = random.choice(list(adjacents[state.terr]))
        return dom


def select_troops(dom, armies: Dict[int, int] = 0):
    state: AttackState = dom.attacking
    max_troops = armies[state.terr] - 1
    if max_troops > 0:
        state.troops = random.choice(range(1, max_troops + 1))
        return dom


def add_to_plan(dom, plan: AttackPlan = None):
    state: AttackState = dom.attacking
    step = AttackStep(
        attacker=state.terr,
        defender=state.adjacent,
        troops=state.troops,
    )
    plan.add_step(step)
    state.attacks += 1
    state.plan = plan
    return dom


### methods
def attack(dom, arg, attacks):
    state: AttackState = dom.attacking
    if state.attacks < attacks:
        return [
            ("select_terr", state.territories),
            ("select_adj", state.adjacents),
            ("select_troops", state.armies),
            ("add_to_plan", state.plan),
            ("attacking", arg, attacks),
        ]
    else:
        return False


def halt_attack(dom, arg, attacks):
    state: AttackState = dom.attacking
    if state.attacks == attacks:
        return []
    else:
        return False

### helpers

def create_state(player: int, attacks: int, game_state: GameState) -> object:

    terrs = game_state.get_territories_owned_by(player)
    adjacents = {t.id: set(o.id for o in t.adjacent_territories) for t in terrs}
    armies = {t.id: t.armies for t in terrs}

    dom = ghop.State(
        "attack_domain",
        **{
            "attacking": AttackState(
                player=player,
                attacks=0,
                adjacents=adjacents,
                territories=set(t.id for t in terrs),
                armies=armies,
                plan=AttackPlan(attacks),
            )
        },
    )

    return dom


def create_planner():
    ghop.current_domain = ghop.Domain("htn_random_placement")
    ghop.declare_actions(select_terr, select_adj, select_troops, add_to_plan)
    ghop.declare_unigoal_methods("attacking", attack, halt_attack)


class RandomAttacks:
    """
    Randomly selects territories and troop attacks.
    """

    @staticmethod
    def construct_plan(
        player: int, max_attacks: int, atk_prob: float, game_state: GameState
    ) -> AttackPlan:

        attack = 0
        pick = random.random()
        while attack < max_attacks and pick < atk_prob:
            attack += 1
            pick = random.random()

        dom = create_state(player, attack, game_state)
        create_planner()
        _ = ghop.find_plan(dom, [("attacking", "attacks", attack)])

        return dom.attacking.plan


if __name__ == "__main__":

    game_state = GameState.create_new_game(20, 5, 50)
    game_state.initialise()

    ghop.verbose = 4

    max_attacks = 10

    plan = RandomAttacks.construct_plan(
        player=0, max_attacks=max_attacks, atk_prob=0.75, game_state=game_state
    )

    print(f"Generated Attack Plan: {str(plan)}")
    for step in plan.steps:
        print(step)
    assert len(plan) <= max_attacks
