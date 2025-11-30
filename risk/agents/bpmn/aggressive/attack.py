from ...plans import Planner


class AttackPlanner(Planner):
    """
    Planner for aggressive deploying attacks.
    """

    def __init__(self, agent):
        super().__init__(agent)

    def construct_plan(self, state):
        return super().construct_plan(state)