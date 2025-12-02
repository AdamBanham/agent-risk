from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug, info
from risk.utils import map as mapping

import random

class AttackPlanner(Planner):
    """
    A defensive attack planner.
    """

    def __init__(self, player: int, max_attacks: int):
        super().__init__()
        self.player = player
        self.max_attacks = max_attacks

    def construct_plan(self, game_state: GameState) -> AttackPlan:
        plan = AttackPlan(self.max_attacks)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(20, 2, 50)
    state.initialise()
    state.update_player_statistics()

    fronts = mapping.construct_safe_view(state.map, 0).frontline_nodes
    front = random.choice(list(fronts))
    terr = state.get_territory(front.id)
    terr.armies += 100

    state.update_player_statistics()

    planner = AttackPlanner(0, 2)
    plan = planner.construct_plan(state)

    info("Constructed Plan: {}".format(plan))
    assert len(plan.steps) > 0, "Expected at least an attack in the plan."
    for step in plan.steps:
        info(" - Step: {}".format(step))
