from ...plans import Planner, AttackPlan


class RandomAttacks(Planner):
    """
    A planner that generates random attack plans.
    """

    def generate_attack_plan(self, state, player_id) -> "AttackPlan":
        # Implement logic to create a random attack plan
        return AttackPlan(attacks=3)
