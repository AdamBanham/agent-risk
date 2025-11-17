from ...plans import Planner, PlacementPlan, TroopPlacementStep
from risk.state import GameState
from risk.utils.logging import debug

from typing import Set

from xdevs.models import Atomic, Coupled, Port
from xdevs.sim import Coordinator


from .base import Selector, Reworker


class Builder(Atomic):
    """
    An atomic model that builds a TroopPlacementStep from a territory ID.
    """

    def __init__(self, name: str):
        super().__init__(name)

        self.i_terr = Port(int, "i_terr")
        self.o_step = Port(TroopPlacementStep, "o_step")

        self._step = None

        self.add_in_port(self.i_terr)
        self.add_out_port(self.o_step)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug("Builder internal transition")
        self._step = None
        self.passivate()

    def deltext(self, e):
        debug("Builder external transition")
        if self.i_terr:
            terr_id: int = self.i_terr.get()
            self._step = TroopPlacementStep(territory=terr_id, troops=1)
            self.activate()

    def lambdaf(self):
        debug("Builder output function")
        if self._step is not None:
            debug(f"Builder created step: {self._step}")
            self.o_step.add(self._step)

    def exit(self):
        return super().exit()


class PlacementModel(Coupled):
    """
    A coupled model that implements a random placement planner.
    """

    def __init__(self, name, terrs: Set[int], placements: int):
        super().__init__(name)

        self.placements = placements

        self.selector = Selector("selector")
        self.builder = Builder("builder")
        self.reworker = Reworker[TroopPlacementStep](
            "reworker", terrs, reworks=placements
        )

        self.add_component(self.selector)
        self.add_component(self.builder)
        self.add_component(self.reworker)

        self.add_coupling(self.reworker.o_request, self.selector.i_terrs)
        self.add_coupling(self.selector.o_terr, self.builder.i_terr)
        self.add_coupling(self.builder.o_step, self.reworker.i_action)

    def initialize(self):
        super().initialize()

    def start_planning(self):
        coordinator = Coordinator(self)
        coordinator.initialize()
        coordinator.simulate()
        done_steps = self.reworker.get_actions()
        return done_steps


class RandomPlacement(Planner):
    """
    A planner that generates random placement plans.
    """

    def __init__(self, player_id: int, placements_left: int):
        super().__init__()
        self.player_id = player_id
        self.placements_left = placements_left
        self._sim = None

    def construct_plan(self, game_state: GameState) -> PlacementPlan:
        plan = PlacementPlan(self.placements_left)

        terrs = {t.id for t in game_state.get_territories_owned_by(self.player_id)}

        model = PlacementModel("random_placement_model", terrs, self.placements_left)
        steps = model.start_planning()

        for step in steps:
            plan.add_step(step)

        return plan


if __name__ == "__main__":
    from logging import DEBUG
    from risk.utils.logging import setLevel

    setLevel(DEBUG)

    state = GameState.create_new_game(52, 2, 50)
    state.initialise()
    state.update_player_statistics()

    planner = RandomPlacement(0, 5)
    plan = planner.construct_plan(state)

    print(plan)
    for step in plan.steps:
        print(step)
