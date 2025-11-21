from py_trees.behaviour import Behaviour
from py_trees.composites import Selector as Selection
from py_trees.common import Status
from py_trees.common import Access

from dataclasses import dataclass
from abc import abstractmethod
import inspect
import random
from typing import Callable, List

from risk.state.plan import Plan
from risk.utils.logging import debug


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
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client(self.bd_name)
        self.bd.register_key(key="state", access=Access.READ)

    def update(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        # Check if we have placements remaining
        state: StateWithPlan = self.bd.state
        if not state.plan.goal_achieved(self.game_state):
            debug("Plan not Acheived.")
            return Status.SUCCESS
        else:
            debug("Plan Acheived.")
            return Status.FAILURE

    def terminate(self, new_status):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
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
        super().__init__("Select from {} to put in {}".format(attr_name, put_name))
        self.state_name = state_name
        self.attr_name = attr_name
        self.put_name = put_name
        self.replacement = with_replacement
        if not condition:
            self.condition = lambda x: True
        else:
            self.condition = condition

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
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
            debug("No valid values to select from.")
            return Status.FAILURE
        terr = random.choice(values)
        if not self.replacement:
            values.remove(terr)
            setattr(state, self.attr_name, values)
            debug(f"Selected {terr}, remaining: {values}")
        setattr(state, self.put_name, terr)
        return Status.SUCCESS

    def terminate(self, new_status):
        return super().terminate(new_status)


class Compute(Behaviour):
    """
    Performs a computation using a provided blackboard and
    stores the result back on the blackboard.

    :param state_name: Name of the blackboard to read from
    :param put_name: Name of the attribute to put the computed value into

    :method compute(state) -> Any: Computes the value based on the state.
        Must be implemented by subclasses.
    """

    def __init__(self, state_name: str, put_name: str):
        super().__init__("Computing value for {}".format(put_name))
        self.state_name = state_name
        self.put_name = put_name

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client(self.state_name)
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state = self.bd.state
        value = self.compute(state)
        setattr(state, self.put_name, value)
        return Status.SUCCESS

    @abstractmethod
    def compute(self, state):
        pass


class PutInto(Behaviour):
    """
    Places a value on the blackboard into a collection on
    the blackboard.

    :param state_name: Name of the blackboard to read from
    :param from_name: Name of the attribute to read value from
    :param to_name: Name of the attribute to put the value into
    :param key: Optional key to use from the blackboard as the key
        for dictionary collections.
    """

    def __init__(
        self,
        state_name: str,
        from_name: str,
        to_name: str,
        key: str,
    ):
        super().__init__("Put {} into {}".format(from_name, to_name))
        self.state_name = state_name
        self.from_name = from_name
        self.to_name = to_name
        self.key_name = key

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client(self.state_name)
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state = self.bd.state
        value = getattr(state, self.from_name)
        collection = getattr(state, self.to_name)
        if isinstance(collection, dict):
            if self.key_name is not None:
                key = getattr(state, self.key_name)
                collection[key] = value
            else:
                debug("No key provided for dictionary collection.")
                return Status.FAILURE
        elif isinstance(collection, list):
            collection.append(value)
        elif isinstance(collection, set):
            collection.add(value)
        else:
            debug(f"Unsupported collection type: {type(collection)}")
            return Status.FAILURE
        setattr(state, self.to_name, collection)
        return Status.SUCCESS


class GetBestFrom(Behaviour):
    """
    Reterives the best value from a collection on the blackboard.

    :param state_name: Name of the blackboard to read from
    :param from_name: Name of the attribute to read values from
    :param to_name: Name of the attribute to put the best value into

    :method best(collection) -> object: Determines the best value
        from the collection. Must be implemented by subclasses.
    """

    def __init__(self, state_name: str, from_name: str, to_name: str):
        super().__init__("Finding best in {}".format(from_name))
        self.state_name = state_name
        self.from_name = from_name
        self.to_name = to_name

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        self.bd = self.attach_blackboard_client(self.state_name)
        self.bd.register_key(key="state", access=Access.WRITE)
        return super().initialise()

    def update(self):
        state = self.bd.state
        collection = getattr(state, self.from_name)
        if not collection:
            debug("No values in collection to select best from.")
            return Status.FAILURE
        best_value = self.best(collection)
        setattr(state, self.to_name, best_value)
        return Status.SUCCESS

    @abstractmethod
    def best(self, collection) -> object:
        """
        Determines the best value from the collection and
        returns it.
        """
        pass


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
        super().__init__("Checking {}".format(attr_name))
        self.state_name = state_name
        self.attr_name = attr_name
        self.condition = condition

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
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
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
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


class ExecuteIf(Selection):
    """
    Executes a child behaviour only if all the given checkers return
    false.

    :param condition: Condition to check
    """

    def __init__(
        self,
        name: str,
        checks: List[Checker],
        child: Behaviour,
    ):
        super().__init__(name, False, [])

        self.add_children(checks + [child])

    def initialise(self):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        return super().initialise()

    def terminate(self, new_status):
        debug(f"{self.__class__.__name__}::{self.name}::{func_name()}")
        return super().terminate(new_status)
