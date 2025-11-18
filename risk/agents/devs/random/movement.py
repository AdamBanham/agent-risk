from ...plans import Planner, MovementPlan, RouteMovementStep, MovementStep
from risk.state import GameState
from risk.utils.movement import find_movement_sequence
from risk.utils.movement import find_safe_frontline_territories
from risk.utils.movement import find_connected_frontline_territories
from risk.utils.logging import debug

from typing import Set, Dict

from .base import Selector, Reworker, SelectFrom
from xdevs.sim import Coupled, Port, Atomic
from xdevs.sim import Coordinator


class Builder(Atomic):
    """
    An atomic model that builds a TroopPlacementStep from a territory ID.
    """

    def __init__(self, name: str):
        super().__init__(name)

        self.i_safe = Port(int, "i_safe")
        self.i_front = Port(int, "i_front")
        self.i_troops = Port(int, "i_troops")
        self.o_step = Port(MovementStep, "o_step")

        self._safe = None
        self._front = None
        self._troops = None
        self._step = None

        self.add_in_port(self.i_safe)
        self.add_in_port(self.i_front)
        self.add_in_port(self.i_troops)
        self.add_out_port(self.o_step)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug("Builder internal transition")
        if self._step is not None:
            self._safe = None
            self._front = None
            self._troops = None
            self._step = None
            self.passivate()

    def deltext(self, e):
        debug("Builder external transition")
        if self.i_safe:
            self._safe = self.i_safe.get()
        if self.i_front:
            self._front = self.i_front.get()
        if self.i_troops:
            self._troops = self.i_troops.get()
        self.activate()

    def lambdaf(self):
        debug("Builder output function")
        if (
            self._safe is not None
            and self._front is not None
            and self._troops is not None
        ):
            self._step = MovementStep(
                source=self._safe,
                destination=self._front,
                troops=self._troops,
            )
            debug(f"Builder created step: {self._step}")
            self.o_step.add(self._step)

    def exit(self):
        return super().exit()


class MovementModel(Coupled):
    """
    A coupled model for random movement planning, moving troops
    from one random safe territory to a random frontline territory.
    """

    def __init__(
        self,
        player_id: int,
        max_moves: int,
        safes: Set[int],
        frontlines: Dict[int, Set[int]],
        armies=Dict[int, int],
    ):
        super().__init__("RandomMovementModel")
        self.player_id = player_id
        self.max_moves = max_moves

        self.selector_safe = Selector("SafeTerritorySelector")
        self.selector_frontline = SelectFrom[int, int](
            "FrontlineTerritorySelector",
            frontlines,
        )
        self.selector_armies = SelectFrom[int, int](
            "ArmiesSelector",
            armies,
        )
        self.builder = Builder("MovementStepBuilder")
        self.reworker = Reworker[MovementStep]("MovementStepReworker", safes, max_moves)

        self.add_component(self.selector_safe)
        self.add_component(self.selector_frontline)
        self.add_component(self.selector_armies)
        self.add_component(self.builder)
        self.add_component(self.reworker)

        self.add_coupling(self.reworker.o_request, self.selector_safe.i_terrs)
        self.add_coupling(self.selector_safe.o_terr, self.selector_frontline.i_terrs)
        self.add_coupling(self.selector_safe.o_terr, self.selector_armies.i_terrs)
        self.add_coupling(self.selector_safe.o_terr, self.builder.i_safe)
        self.add_coupling(self.selector_frontline.o_terr, self.builder.i_front)
        self.add_coupling(self.selector_armies.o_terr, self.builder.i_troops)
        self.add_coupling(self.builder.o_step, self.reworker.i_action)

    def start_planning(self):
        coordinator = Coordinator(self)
        coordinator.initialize()
        coordinator.simulate()
        actions = self.reworker.get_actions()
        return actions


class RandomMovement(Planner):
    """
    A planner that generates random movement plans.
    """

    def __init__(self, player_id: int, max_moves: int):
        super().__init__()
        self.player_id = player_id
        self.max_moves = max_moves

    def construct_plan(self, game_state: GameState) -> MovementPlan:
        safes, frontlines = find_safe_frontline_territories(
            game_state=game_state, player_id=self.player_id
        )
        safes_ids = set(t.id for t in safes)
        connections = dict(
            (
                s.id,
                set(
                    o.id
                    for o in find_connected_frontline_territories(
                        s, frontlines, safes + frontlines
                    )
                ),
            )
            for s in safes
        )
        armies = {s.id: [s.armies - 1] for s in safes}
        safes_ids = set(
            s
            for s in safes_ids
            if len(connections.get(s)) > 0 and armies.get(s, [0])[0] > 0
        )

        plan = MovementPlan(self.max_moves)

        if len(safes_ids) == 0:
            return plan

        model = MovementModel(
            player_id=self.player_id,
            max_moves=self.max_moves,
            safes=safes_ids,
            frontlines=connections,
            armies=armies,
        )
        actions = model.start_planning()

        for action in actions:
            movement = find_movement_sequence(
                game_state.get_territory(action.source),
                game_state.get_territory(action.destination),
                action.troops,
            )
            steps = [
                MovementStep(
                    source=step.src.id,
                    destination=step.tgt.id,
                    troops=step.amount,
                )
                for step in movement
            ]
            plan.add_step(RouteMovementStep(steps, action.troops))

        return plan


if __name__ == "__main__":
    from risk.state import GameState
    from risk.utils.replay import simulate_turns
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)

    state = GameState.create_new_game(50, 2, 200)
    state, _ = simulate_turns(state, 150)

    planner = RandomMovement(player_id=0, max_moves=1)
    plan = planner.construct_plan(state)

    print(plan)
    for step in plan.steps:
        print(step)

    planner = RandomMovement(player_id=1, max_moves=1)
    plan = planner.construct_plan(state)

    print(plan)
    for step in plan.steps:
        print(step)
