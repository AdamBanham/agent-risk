from ...plans import Planner


class AttackPlanner(Planner):
    """
    Planner for aggressive deploying attacks.
    """

    def __init__(self, player: int, max_attacks: int):
        super().__init__()
        self.player = player
        self.max_attacks = max_attacks

    def construct_plan(self, state):
        return super().construct_plan(state)
