from risk.state.plan import Step, Plan, Goal
from risk.state.event_stack import TroopPlacementEvent, AttackOnTerritoryEvent

from copy import deepcopy


class TroopPlacementStep(Step):
    """
    A step that produces a placement of troops on a territory.
    """

    def __init__(self, territory: int, troops: int):
        super().__init__(f"A placement of {troops} troops on a territory {territory}")
        self.territory = territory
        self.troops = troops

    def execute(self, state):
        return [
            TroopPlacementEvent(
                state.current_turn,
                state.current_player_id,
                self.territory,
                self.troops,
            )
        ]


class CreatePlacements(Goal):
    """
    A goal of making N placements on the board for risk.
    """

    def __init__(self, placements: int):
        super().__init__("A goal to have a plan that could place n troops")
        self.placements = placements

    def achieved(self, state, plan: Plan):
        curr_plan = deepcopy(plan)
        troops = 0
        while not curr_plan.is_done():
            step = curr_plan.pop_step()
            if isinstance(step, TroopPlacementStep):
                troops += step.troops

        return troops == self.placements


class PlacementPlan(Plan):
    """
    A plan for the placement phase of risk
    """

    def __init__(
        self,
        placements: int,
    ):
        super().__init__(
            "Agent's plan for its placement phase", CreatePlacements(placements)
        )


class AttackStep(Step):
    """
    A step that requests an attack on a territory from another, with
    some amount of troops.
    """

    def __init__(self, attacker: int, defender: int, troops: int):
        super().__init__(f"Attacking {defender} from {attacker} with {troops} troops")
        self.attacker = attacker
        self.defender = defender
        self.troops = troops

    def execute(self, state):
        return [
            AttackOnTerritoryEvent(
                state.current_player_id,
                state.current_turn,
                self.attacker,
                self.defender,
                self.troops,
            )
        ]


class AttackFrequency(Goal):
    """
    A goal to launch up to N attacks in an attack plan.
    """

    def __init__(self, attacks: int):
        super().__init__(f"Create {attacks} requests to launch.")
        self.num_attacks = attacks

    def achieved(self, state, plan):
        attacks = 0
        for step in plan.steps:
            if isinstance(step, AttackStep):
                attacks += 1
        return attacks <= self.num_attacks


class AttackPlan(Plan):
    """
    A plan for the placement phase of risk
    """

    def __init__(
        self,
        attacks: int,
    ):
        super().__init__("Agent's plan for its attack phase", AttackFrequency(attacks))
