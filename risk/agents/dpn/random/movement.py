from ...plans import Planner, MovementPlan

class RandomMovement(Planner):
    """
    A planner that generates random routes between safe and
    frontline territories for movement plans.
    """

    def generate_movement_plan(self, state, player_id) -> "MovementPlan":
        # Implement logic to create a random movement plan
        return MovementPlan(moves=3)