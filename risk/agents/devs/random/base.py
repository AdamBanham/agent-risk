"""
Base constructs for random DEVS agents.
"""

from risk.utils.logging import debug
from xdevs.models import Atomic, Port

from typing import Set, List, Dict
import random


class Selector(Atomic):
    """
    An atomic model that takes a set of territories and selects one at random.

    Ports:
    - Input: 'i_terrs' (Set[int]) - A set of territory IDs to choose from.
    - Output: 'o_terr' (int) - The selected territory ID.

    """

    def __init__(self, name: str):
        super().__init__(name)

        self.i_terrs = Port(set, "i_terrs")
        self.o_terr = Port(int, "o_terr")

        self._terrs = None
        self._selected = None

        self.add_in_port(self.i_terrs)
        self.add_out_port(self.o_terr)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug(f"Selector::{self.name} internal transition")
        self._selected = None
        self._terrs = None
        self.passivate()

    def deltext(self, e):
        debug(f"Selector::{self.name} external transition")
        if self.i_terrs:
            self._terrs: Set[int] = self.i_terrs.get()
            self._selected = random.choice(list(self._terrs))
            debug(f"Selector::{self.name} selected territory: {self._selected}")
            self.activate()

    def lambdaf(self):
        debug(f"Selector::{self.name} output function")
        if self._selected is not None:
            debug(f"Selector::{self.name} selected territory: {self._selected}")
            self.o_terr.add(self._selected)

    def exit(self):
        return super().exit()

    def output(self):
        pass


class SelectFrom[T, J](Selector):
    """
    Selector that selects from a given mapping of choices.
    Other services send the key of the mapping to select from.
    """

    def __init__(self, name: str, choices: Dict[T, J]):
        super().__init__(name)
        self.choices = choices

    def deltext(self, e):
        debug(f"SelectFrom::{self.name} external transition")
        if self.i_terrs:
            key: T = self.i_terrs.get()
            if key in self.choices:
                options: Set[J] = self.choices[key]
                self._selected = random.choice(list(options))
                debug(f"SelectFrom::{self.name} selected option: {self._selected}")
                self.activate()
            else:
                debug(f"SelectFrom::{self.name} key {key} not in choices.")


class Picker(Atomic):
    """
    An atomic model that given some maximum number, outputs
    a random number between 1 and that maximum.
    """

    def __init__(self, name):
        super().__init__(name)

        self.i_max = Port(int, "i_max")
        self.o_pick = Port(int, "o_pick")

        self._max = None
        self._pick = None
        self.add_in_port(self.i_max)
        self.add_out_port(self.o_pick)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug("Picker internal transition")
        self._pick = None
        self._max = None
        self.passivate()

    def deltext(self, e):
        debug("Picker external transition")
        if self.i_max:
            self._max = self.i_max.get()
            if self._max > 0:
                self._pick = random.randint(1, self._max)
            else:
                self._pick = 0
            debug(f"Picker picked number: {self._pick}")
            self.activate()

    def lambdaf(self):
        debug("Picker output function")
        if self._pick is not None:
            debug(f"Picker picked number: {self._pick}")
            self.o_pick.add(self._pick)

    def exit(self):
        return super().exit()


class Reworker[T](Atomic):
    """
    An atomic model that collects steps and sends out request
    for further steps as needed.
    """

    def __init__(self, name: str, terrs: Set[int], reworks: int):
        super().__init__(name)

        self.reworks_left = reworks
        self.actions: List[T] = []
        self.terrs = terrs

        self.i_action = Port(T, "i_action")
        self.o_fin = Port(list, "o_fin")
        self.o_request = Port(set, "o_request")

        self.add_in_port(self.i_action)
        self.add_out_port(self.o_fin)
        self.add_out_port(self.o_request)

    def initialize(self):
        if self.reworks_left > 0:
            self.activate()

    def deltint(self):
        self.passivate()

    def deltext(self, e):
        if self.i_action:
            step: T = self.i_action.get()
            debug(f"Reworker::{self.name} received action: {step}")
            self.actions.append(step)
            self.reworks_left -= 1
            self.activate()

    def lambdaf(self):
        if self.reworks_left > 0:
            self.o_request.add(self.terrs)
            debug(f"Reworker::{self.name} requesting more placements. Left: {self.reworks_left}")
        else:
            self.o_fin.add(self.actions)
            debug(f"Reworker::{self.name} sending done signal with all actions.")

    def exit(self):
        return super().exit()

    def get_actions(self) -> List[T]:
        return self.actions
