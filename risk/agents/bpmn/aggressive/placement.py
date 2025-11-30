from ...plans import Planner


class PlacementPlanner(Planner):
    """
    Planner for aggressive placing troops.
    """

    def __init__(self, agent):
        super().__init__(agent)

    def construct_plan(self, state):
        return super().construct_plan(state)
