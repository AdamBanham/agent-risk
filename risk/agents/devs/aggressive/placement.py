from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState
from risk.utils.logging import debug, info


class PlacementPlanner(Planner):
    """
    An aggressive placement planner.
    """

    def __init__(self, player: int, placements: int):
        super().__init__()
        self.player = player
        self.placements = placements

    def construct_plan(self, game_state: GameState) -> PlacementPlan:
        plan = PlacementPlan(self.placements)

        return plan


if __name__ == "__main__":
    from risk.utils.logging import setLevel
    from logging import DEBUG

    setLevel(DEBUG)

    state = GameState.create_new_game(20, 2, 50)
    state.initialise()
    state.update_player_statistics()

    planner = PlacementPlanner(0, 2)
    plan = planner.construct_plan(state)

    info("Constructed Plan: {}".format(plan))
    assert len(plan.steps) == 2, "Expected 2 placement steps in the plan."
    for step in plan.steps:
        info(" - Step: {}".format(step))
