from copy import deepcopy
from dataclasses import dataclass
from typing import Collection
import random

from risk.state.plan import Plan
from risk.utils.logging import debug


@dataclass
class HTNStateWithPlan:
    player: int
    plan: Plan = None

    def get(self, key: str):
        return getattr(self, key)

    def display(self):
        return str(self)

    def copy(self):
        return deepcopy(self)

    def __getitem__(self, key: str):
        return getattr(self, key)


# low level commands for actions
def c_append(dom, namespace: str, key: str, value: object) -> object:
    state = getattr(dom, namespace, None)
    debug(f"Command 'add' called to add value: {value} to key: {key}")
    collection: list = getattr(state, key, None)
    collection.append(value)
    setattr(state, key, collection)
    return dom

def c_set(dom, namespace: str, key: str, value: object) -> object:
    state = getattr(dom, namespace, None)
    debug(f"Command 'set' called to set key: {key} to value: {value}")
    setattr(state, key, value)
    return dom


def include_commands():
    from risk.agents.htn import gtpyhop as ghop

    ghop.declare_actions(c_set, c_append)

def include_methods(*methods):
    from risk.agents.htn import gtpyhop as ghop

    for method in methods:
        ghop.declare_methods(method.__name__, method)

# high level abstractions for actions
class Selector:
    """
    An action for selecting from a given collection,
    and placing the result into another state variable.
    Uses random choice to decide what elements to select
    from the given collection.

    :fieldname to_key: The key in the state to place the selected element
    :fieldname namespace: The namespace for state variable to select into

    The class is a callable object, so it can be used as an action in GTpyhop.
    The name of the action will be 'select_{to_key}'.

    ^^^^^^^^
    __call__ method signature
    ^^^^^^^^
        :param dom: The domain state to operate on
        :param collection: The collection to select from
        :returns: The modified domain state with the selected element
    """

    def __init__(self, to_key: str, namespace: str):
        self.to_key = to_key
        self.namespace = namespace
        self.__name__ = f"select_{to_key}"

    def __call__(self, dom: object, collection: Collection | str) -> object:
        state = getattr(dom, self.namespace, None)

        if isinstance(collection, str):
            collection = getattr(state, collection, None)

        debug(
            f"Action '{self.__name__}' called with collection: {collection}",
        )
        if collection:
            if isinstance(collection, set):
                selected = random.choice(list(collection))
            else:
                selected = random.choice(collection)
            debug(f"Action '{self.__name__}' selected: {selected}")
            return [
                ("c_set", self.namespace, self.to_key, selected),
            ]
            setattr(state, self.to_key, selected)
        else:
            debug(f"Action '{self.__name__}' found empty collection, failing.")
            raise RuntimeError("Cannot select from empty collection")

        return dom


class Filter:
    """
    An actions for filtering a collection based on some criteria,
    and placing the filtered result into another state variable.

    :fieldname to_key: The key in the state to place the filtered collection
    :fieldname namespace: The namespace for state variable to filter into
    :fieldname filterer: A callable that filters the collection and returns
        the filtered result

    The class is a callable object, so it can be used as an action in GTpyhop.
    The name of the action will be 'filter_{to_key}'.
    ^^^^^^^^
    __call__ method signature
    ^^^^^^^^
        :param dom: The domain state to operate on
        :param collection: The collection to filter
        :returns: the filtered collection
    """

    def __init__(self, to_key: str, namespace: str, filter: callable):
        self.to_key = to_key
        self.namespace = namespace
        self.filter = filter
        self.__name__ = f"filter_{to_key}"

    def __call__(self, dom: object, collection: Collection | str) -> object:
        state = getattr(dom, self.namespace, None)
        if isinstance(collection, str):
            collection = getattr(state, collection, None)

        debug(f"Action '{self.__name__}' called with collection: {collection}")
        filtered = self.filter(state, collection)
        debug(f"Action '{self.__name__}' filtered result: {filtered}")
        return [
            ("c_set", self.namespace, self.to_key, filtered),
        ]
        setattr(state, self.to_key, filtered)
        return dom


class BuildStep:
    """
    An action for building an action for a plan and adding it to some
    state variable in the domain. The state variable is expected to be a list.

    :fieldname to_key: The key in the state to place the selected element
    :fieldname namespace: The namespace for state variable to select into
    :fieldname builder: A callable that builds the step given the namespace state

    The class is a callable object, so it can be used as an action in GTpyhop.
    The name of the action will be 'build_step'.

    ^^^^^^^^
    __call__ method signature
    ^^^^^^^^
        :param dom: The domain state to operate on
        :returns: The modified domain state with the added step
    """

    def __init__(self, to_key: str, namespace: str, builder: callable):
        self.to_key = to_key
        self.namespace = namespace
        self.builder = builder
        self.__name__ = "build_step"

    def __call__(self, dom: object) -> object:
        state = getattr(dom, self.namespace, None)
        debug(f"Action '{self.__name__}' called to build step for key: {self.to_key}")
        step = self.builder(state)
        debug(f"Action '{self.__name__}' built step: {step}")
        return [
            ("c_append", self.namespace, self.to_key, step),
        ]
        collection: list = getattr(state, self.to_key, None)
        collection.append(step)
        setattr(state, self.to_key, collection)
        setattr(dom, self.namespace, state)
        return dom


class Computer:
    """
    An action for computing a new value for a state variable, useful for
    when you need to derive a value based on other state variables.

    :fieldname to_key: The key in the state to place the computed value
    :fieldname namespace: The namespace for state variable to compute into
    :fieldname computer: A callable that computes the value given the namespace state

    The class is a callable object, so it can be used as an action in GTpyhop.
    The name of the action will be 'compute_{to_key}'.

    ^^^^^^^^
    __call__ method signature
    ^^^^^^^^
        :param dom: The domain state to operate on
        :returns: The modified domain state with the computed value
    """

    def __init__(self, to_key: str, namespace: str, computer: callable):
        self.to_key = to_key
        self.namespace = namespace
        self.computer = computer
        self.__name__ = f"compute_{to_key}"

    def __call__(self, dom: object) -> object:
        state = getattr(dom, self.namespace, None)
        debug(
            f"Action '{self.__name__}' called to compute value for key: {self.to_key}"
        )
        value = self.computer(state)
        debug(f"Action '{self.__name__}' computed value: {value}")
        return [
            ("c_set", self.namespace, self.to_key, value),
        ]
        setattr(state, self.to_key, value)
        return dom


class Reseter:
    """
    An action for resetting a state variable to a default value.

    :fieldname key: The key in the state to reset
    :fieldname namespace: The namespace for state variable to reset
    :fieldname default: The default value to reset to

    The class is a callable object, so it can be used as an action in GTpyhop.
    The name of the action will be 'reset_{to_key}'.

    ^^^^^^^^
    __call__ method signature
    ^^^^^^^^
        :param dom: The domain state to operate on
        :returns: The modified domain state with the reset value
    """

    def __init__(self, key: str, namespace: str, default: object):
        self.key = key
        self.namespace = namespace
        self.default = default
        self.__name__ = f"reset_{key}"

    def __call__(self, dom: object) -> object:
        state = getattr(dom, self.namespace, None)
        debug(f"Action 'reset_{self.key}' called to reset value for key: {self.key}")
        return [
            ("c_set", self.namespace, self.key, self.default),
        ]
        setattr(state, self.key, self.default)
        return dom
