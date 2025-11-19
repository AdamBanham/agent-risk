from py_trees.behaviour import Behaviour
from py_trees.common import Status
from py_trees.common import Access

from dataclasses import dataclass
from abc import abstractmethod
import inspect
import random
from typing import Callable

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


class Selector(Behaviour):
    """
    Selects a random value from a blackboard attribute.

    :param state_name: Name of the blackboard to read from
    :param attr_name: Name of the attribute to read values from
    :param put_name: Name of the attribute to put the selected value into
    :param condition: Optional condition to filter values
    """

    def __init__(
        self,
        state_name: str,
        attr_name: str,
        put_name: str = "terr",
        condition: Callable = None,
        with_replacement: bool = True,
    ):
        super().__init__("Select from Blackboard")
        self.state_name = state_name
        self.attr_name = attr_name
        self.put_name = put_name
        self.replacement = with_replacement
        if not condition:
            self.condition = lambda x: True
        else:
            self.condition = condition

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.bd = self.attach_blackboard_client(self.state_name)
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state = self.bd.state
        values = getattr(state, self.attr_name)
        if isinstance(values, set):
            values = list(values)
        values = list(filter(self.condition, values))
        if len(values) == 0:
            return Status.FAILURE
        terr = random.choice(values)
        if not self.replacement:
            values.remove(terr)
            setattr(state, self.attr_name, values)
        setattr(state, self.put_name, terr)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class Checker(Behaviour):
    """
    Checks if a condition is met on a blackboard attribute.

    :param state_name: Name of the blackboard to read from
    :param attr_name: Name of the attribute to read values from
    :param condition: Condition to check
    """

    def __init__(
        self,
        state_name: str,
        attr_name: str,
        condition: Callable,
    ):
        super().__init__("Check Blackboard Condition")
        self.state_name = state_name
        self.attr_name = attr_name
        self.condition = condition

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.bd = self.attach_blackboard_client(self.state_name)
        self.bd.register_key(key="state", access=Access.READ)
        return super().initialise()

    def update(self):
        state = self.bd.state
        value = getattr(state, self.attr_name)
        if self.condition(value):
            return Status.SUCCESS
        else:
            return Status.FAILURE

    def terminate(self, new_status):
        return super().terminate(new_status)


class BuildAction(Behaviour):
    """
    Builds an action step and adds it to the plan.

    :param state_name: Name of the blackboard to read from
    :param attr_name: Name of the attribute to append the action to

    Has an abstract method 'build_step' that must be implemented by subclasses.
    :method build_step(state) -> ActionStep: Builds the action step
    based on the state.
    """

    def __init__(
        self,
        name: str,
        state_name: str,
        attr_name: str,
    ):
        super().__init__(name)
        self.state_name = state_name
        self.attr_name = attr_name

    def initialise(self):
        self.logger.debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self._ticks = 0
        self.bd = self.attach_blackboard_client(self.state_name)
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state = self.bd.state
        values = getattr(state, self.attr_name)
        step = self.build_step(state)
        values.append(step)
        setattr(state, self.attr_name, values)
        return Status.SUCCESS

    @abstractmethod
    def build_step(self, state) -> object:
        pass

    def terminate(self, new_status):
        return super().terminate(new_status)
