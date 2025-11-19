from ...plans import Planner, AttackPlan, AttackStep
from risk.state import GameState
from risk.utils.logging import debug


class AttackPlanner(Planner):
    """
    A planner that creates an attack plan based on the current game state.
    """

    def __init__(
        self,
        player_id: int,
        max_attacks: int,
        attack_probability: float = 0.5,
    ):
        super().__init__()
        self.player_id = player_id
        self.max_attacks = max_attacks
        self.attack_probability = attack_probability

    def construct_plan(self, state: GameState) -> AttackPlan:
        return super().construct_plan(state)


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)
