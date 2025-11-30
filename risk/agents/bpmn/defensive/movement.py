from ...plans import Planner


class MovementPlanner(Planner):
    """
    Planner for aggressive moving troops.
    """

    def __init__(self, player: int, max_moves: int):
        super().__init__()
        self.player = player
        self.max_moves = max_moves

    def construct_plan(self, state):
        return super().construct_plan(state)
