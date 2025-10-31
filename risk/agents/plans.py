from abc import abstractmethod
from typing import List, Protocol
from risk.state.event_stack.events.turns import MovementOfTroopsEvent
from risk.state.game_state import GameState
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


class MovementStep(Step):
    """
    A step that requests a movement of troops from one territory to another.
    """

    def __init__(self, source: int, destination: int, troops: int):
        super().__init__(f"Move {troops} troops from {source} to {destination}")
        self.source = source
        self.destination = destination
        self.troops = troops

    def execute(self, state):
        return [
            MovementOfTroopsEvent(
                state.current_player_id,
                state.current_turn,
                self.source,
                self.destination,
                self.troops,
            )
        ]


class RouteMovementStep(Step):
    """
    A step that requests a movement of troops along a route of territories.
    """

    def __init__(self, route: List[MovementStep], troops: int):
        super().__init__(f"Move {troops} troops along route {route}")
        self.route = route
        self.troops = troops

    def add_to_route(self, territory: int):
        self.route.append(territory)

    def execute(self, state):
        events = []
        for step in reversed(self.route):
            events.extend(step.execute(state))
        return events


class MovementFrequency(Goal):
    """
    A goal to launch up to N movements in a movement plan.
    """

    def __init__(self, movements: int):
        super().__init__(f"Create {movements} requests to move.")
        self.num_movements = movements

    def achieved(self, state, plan):
        movements = 0
        for step in plan.steps:
            if isinstance(step, (MovementStep, RouteMovementStep)):
                movements += 1
        return movements <= self.num_movements


class MovementPlan(Plan):
    """
    A plan for the movement phase of risk
    """

    def __init__(
        self,
        moves: int,
    ):
        super().__init__(
            "Agent's plan for its movement phase", MovementFrequency(moves)
        )


class Planner(Protocol):
    """
    A behavioural interface for planning agents.
    """

    @abstractmethod
    def construct_plan(self, state: GameState) -> Plan:
        """
        Constructs a plan for the given game state.
        """
        pass
