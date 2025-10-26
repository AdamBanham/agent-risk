from py_trees.behaviour import Behaviour
from py_trees.common import Status
from py_trees.common import Access

from dataclasses import dataclass
import inspect
import random

from risk.state.plan import Plan


def func_name():
    return inspect.stack()[1].function


@dataclass
class StateWithPlan:
    player: int
    plan: Plan = None


class CheckPlan(Behaviour):

    def __init__(self, game_state, state_name: str):
        super().__init__("Check Plan")
        self.game_state = game_state
        self.bd_name = state_name

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client(self.bd_name)
        self.bd.register_key(key="state", access=Access.READ)

    def update(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        # Check if we have placements remaining
        state: StateWithPlan = self.bd.state
        if not state.plan.goal_achieved(self.game_state):
            self.logger.debug("Plan not Acheived.")
            return Status.SUCCESS
        else:
            self.logger.debug("Plan Acheived.")
            return Status.FAILURE

    def terminate(self, new_status):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        return super().terminate(new_status)


class SelectTerritory(Behaviour):
    """
    Selects a random territory.
    """

    def __init__(self, state_name: str, attr_name: str, put_name: str = "terr"):
        super().__init__("Select Territory")
        self.state_name = state_name
        self.attr_name = attr_name
        self.put_name = put_name

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.placement = self.attach_blackboard_client(self.state_name)
        self.placement.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state = self.placement.state
        values = getattr(state, self.attr_name)
        if isinstance(values, set):
            values = list(values)
        terr = random.choice(values)
        setattr(state, self.put_name, terr)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)
