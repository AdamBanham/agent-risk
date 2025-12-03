"""
Base constructs for random DEVS agents.
"""

from risk.utils.logging import debug
from abc import abstractmethod
from xdevs.models import Atomic, Port, Coupled

from typing import Set, List, Dict, Collection
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


class SelectFrom[K, V](Selector):
    """
    Selector that selects from a given mapping of choices.
    Other services send the key of the mapping to select from.
    """

    def __init__(self, name: str, choices: Dict[K, Collection[V]]):
        super().__init__(name)
        self.choices = choices

    def deltext(self, e):
        debug(f"SelectFrom::{self.name} external transition")
        if self.i_terrs:
            key: K = self.i_terrs.get()
            if key in self.choices:
                options: Set[V] = self.choices[key]
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
    for more until the required number of reworks is reached.

    :param name: Name of the atomic model
    :param terrs: Set of territory IDs to choose from
    :param reworks: Number of actions to collect before finishing

    .. ports ::
        i_action
           Type T:
           produced actions should be sent back here


        o_fin
          Type List[T]:
            once reworks have been completed, this port produces
            the list of collected actions.

        o_request
          Type Set[int]:
            sends out a request to pipeline to
            produce an action from the given input
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
            if step:
                self.actions.append(step)
            self.reworks_left -= 1
            self.activate()

    def lambdaf(self):
        if self.reworks_left > 0:
            self.o_request.add(self.terrs)
            debug(
                f"Reworker::{self.name} requesting more placements. Left: {self.reworks_left}"
            )
        else:
            self.o_fin.add(self.actions)
            debug(f"Reworker::{self.name} sending done signal with all actions.")

    def exit(self):
        return super().exit()

    def get_actions(self) -> List[T]:
        return self.actions


class Builder[T](Atomic):
    """
    An atomic model that builds actions using the given
    input parameter mapping. Calls build function to create
    the action. Subclasses should implement the build function.

    :param name: Name of the atomic model
    :param parameters: Mapping of parameters to used to build the action
     each of these keys corresponds to an input port, i.e., 'i_<key>'.
     The value is the type of the input port.

    .. Methods ::
        build
         Function that takes the input parameters and returns
         an action of type T.

    .. Ports ::
        :port i_<key>: Input port for each parameter key
        :port o_step: Output port for the built action of type T
    """

    def __init__(self, name: str, parameters: Dict[str, type]):
        super().__init__(name)

        self._states = {}
        self.keys = set()
        self._step = None
        
        for key, p_type in parameters.items():
            setattr(self, f"i_{key}", Port(p_type, f"i_{key}"))
            self.add_in_port(getattr(self, f"i_{key}"))
            self.keys.add(key)

        self.i_reset = Port(bool, "i_reset")
        self.add_in_port(self.i_reset)

        self.o_step = Port(object, "o_step")

        self.add_out_port(self.o_step)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug("Builder internal transition")
        self._step = None
        self.passivate()

    @abstractmethod
    def build(self, inputs: Dict[str, any]) -> T:
        """
        Build the action of type T using the given inputs.

        :param inputs: Mapping of input parameter names to their values.
        :return: An action of type T.
        """
        raise NotImplementedError("Subclasses must implement the build method.")

    def deltext(self, e):
        debug("Builder external transition")
        if self.i_reset:
            self.i_reset.empty()
            self._states = {}
            for port in self.in_ports:
                if port:
                    port.empty()
            return self.passivate()
        
        for port in self.in_ports:
            if port:
                value = port.get()
                debug(f"Builder received input on port {port.name}: {value}")
                self._states[port.name[2:]] = value

        all_params = all(self._states.get(key) is not None for key in self.keys)

        if all_params:
            debug(f"Builder has all parameters, building step using {self._states}")
            self._step = self.build(self._states)
            self.activate()

    def lambdaf(self):
        debug("Builder output function")
        if self._step is not None:
            debug(f"Builder created step: {self._step}")
            self.o_step.add(self._step)
            self._states = {}

    def exit(self):
        return super().exit()


class Filter[I, O](Atomic):
    """
    An atomic model that filters the incoming input and
    then outputs the filtered result.

    :param name: Name of the atomic model

    .. methods ::
        filter:
         Function that takes an input of type I and returns
         an output of type O after filtering. Subclasses
         should implement this function.

    .. ports ::
        :port i_filter:
         Input port of type I
        :port o_filtered:
         Output port of type O
        :port o_empty:
         Output port of type bool indicating if the filtered
         output is empty.
    """

    def __init__(self, name=None):
        super().__init__(name)

        self.i_filter = Port(object, "i_filter")
        self.o_filtered = Port(object, "o_filtered")
        self.o_empty = Port(bool, "o_empty")

        self._filterable = None

        self.add_in_port(self.i_filter)
        self.add_out_port(self.o_filtered)
        self.add_out_port(self.o_empty)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug(f"Filter {self.name} internal transition")
        self._filterable = None
        self.passivate()

    def deltext(self, e):
        debug(f"Filter {self.name} external transition")
        if self.i_filter:
            self._filterable = self.i_filter.get()
            debug(f"Filter {self.name} received input: {self._filterable}")
            self.activate()

    @abstractmethod
    def filter(self, item: I) -> O:
        """
        Filter the given input item and return the filtered output.

        :param item: Input item of type I to be filtered.
        :return: Filtered output of type O.
        """
        raise NotImplementedError("Subclasses must implement the filter method.")

    def lambdaf(self):
        debug(f"Filter {self.name} output function")
        if self._filterable is not None:
            filtered = self.filter(self._filterable)
            debug(f"Filter {self.name} produced output: {filtered}")

            if filtered:
                self.o_filtered.add(filtered)
            else:
                self.o_empty.add(False)

    def exit(self):
        return super().exit()


class SeenByFilter[I, O](Filter[Set[I], Set[O]]):
    """
    A filter that keeps track of already seen items from
    its output and only lets unseen items through to the
    filtering function.

    Assumes that the input is a set of items of type I
    and the output is a set of items of type O.

    :param name: Name of the atomic model
    :param seen: Set of already seen items
    """

    def __init__(self, name: str, seen: I = None):
        super().__init__(name)
        if seen is None:
            seen = set()
        self.seen = seen

    def deltext(self, e):
        debug(f"Filter {self.name} external transition")
        if self.i_filter:
            self._filterable = [i for i in self.i_filter.get() if i not in self.seen]
            debug(f"Filter {self.name} received input: {self._filterable}")
            self.activate()

    def lambdaf(self):
        debug(f"Filter {self.name} output function")
        if self._filterable is not None:
            filtered = self.filter(self._filterable)
            debug(f"Filter {self.name} produced output: {filtered}")

            if filtered:
                self.seen.update(filtered)
                debug(f"Filter {self.name} updated seen set: {self.seen}")
                self.o_filtered.add(filtered)
            else:
                self.o_empty.add(False)


class Computer[I, O](Atomic):
    """
    An atomic model that computes an output from the given input.
    Given an input of type I, it produces an output of type O
    by calling the compute function.

    :param name: Name of the atomic model

    .. methods ::
        compute:
         Function that takes an input of type I and returns
         an output of type O after computation. Subclasses
         should implement this function.

    .. ports ::
        :port i_input:
         Input port of type I
        :port o_output:
         Output port of type O
    """

    def __init__(self, name=None):
        super().__init__(name)

        self.i_input = Port(object, "i_input")
        self.i_reset = Port(bool, "i_reset")
        self.o_output = Port(object, "o_output")

        self._input = None

        self.add_in_port(self.i_input)
        self.add_in_port(self.i_reset)
        self.add_out_port(self.o_output)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug(f"Computer {self.name} internal transition")
        self._input = None
        self.passivate()

    def deltext(self, e):
        debug(f"Computer {self.name} external transition")
        if self.i_reset:
            self.i_reset.empty()
            self._input = None
            for port in self.in_ports:
                if port:
                    port.empty()
            return self.passivate()
        if self.i_input:
            self._input = self.i_input.get()
            debug(f"Computer {self.name} received input: {self._input}")
            self.activate()

    @abstractmethod
    def compute(self, item: I) -> O:
        """
        Compute the output from the given input item.

        :param item: Input item of type I to be computed.
        :return: Computed output of type O.
        """
        raise NotImplementedError("Subclasses must implement the compute method.")

    def lambdaf(self):
        debug("Computer output function")
        if self._input is not None:
            output = self.compute(self._input)
            debug(f"Computer {self.name} produced output: {output}")
            self.o_output.add(output)

    def exit(self):
        return super().exit()


class ComputeOnMany[O](Atomic):
    """
    A computer that waits for a range of inputs and computes
    a single output from them.

    :param name: Name of the atomic model
    :param parameters:
     Mapping of parameter names to their types. For each key,
     an input port 'i_<key>' of the given type is created.

    .. ports ::
        :port i_<key>: object - Input port for each parameter key
        :port o_output: O - Output port for the computed output
    """

    def __init__(self, name, parameters: Dict[str, type]):
        super().__init__(name)

        self._keys = set()
        for key, p_type in parameters.items():
            setattr(self, f"i_{key}", Port(p_type, f"i_{key}"))
            self.add_in_port(getattr(self, f"i_{key}"))
            self._keys.add(key)

        self.i_reset = Port(object, "i_reset")
        self.add_in_port(self.i_reset)

        self.o_output = Port(object, "o_output")
        self.add_out_port(self.o_output)

        self._input = {}

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug(f"Computer {self.name} internal transition")
        self._input = {}
        self.passivate()

    def deltext(self, e):
        if self.i_reset:
            self.i_reset.empty()
            self._input = {}
            for port in self.in_ports:
                if port:
                    port.empty()
            self.passivate()

        debug(f"Computer {self.name} external transition")
        for port in self.in_ports:
            if port:
                value = port.get()
                debug(f"Computer {self.name} received input on port {port.name}: {value}")
                self._input[port.name[2:]] = value

        all_params = all(self._input.get(key) is not None for key in self._keys)

        if all_params:
            debug(f"Computer {self.name} has all parameters, computing output using {self._input}")
            self.activate()

    @abstractmethod
    def compute(self, values: Dict[str, object]) -> O:
        """
        Compute the output from the given input item.

        :param item: Input item of type I to be computed.
        :return: Computed output of type O.
        """
        raise NotImplementedError("Subclasses must implement the compute method.")

    def lambdaf(self):
        debug(f"Computer {self.name} output function")
        all_params = all(self._input.get(key) is not None for key in self._keys)

        if all_params:
            output = self.compute(self._input)
            debug(f"Computer {self.name} produced output: {output}")
            self.o_output.add(output)

    def exit(self):
        return super().exit()


class ConditionalXor[I](Atomic):
    """
    An atomic model that given some input, checks
    whether the condition function is met, returning out
    on either o_true or o_false accordingly. If the condition
    is met, the input is sent to o_true, otherwise
    a False boolean is sent to o_false.

    :param name: Name of the atomic model

    .. ports ::
        :port i_input: object - Input port
        :port o_true: bool - Output port for true condition
        :port o_false: bool - Output port for false condition

    .. methods ::
        condition:
         Function that takes an input of type object and returns
         a boolean indicating whether the condition is met.
    """

    def __init__(self, name=None):
        super().__init__(name)

        self.i_input = Port(object, "i_input")
        self.i_reset = Port(bool, "i_reset")
        self.o_true = Port(object, "o_true")
        self.o_false = Port(bool, "o_false")

        self._input = None
        self.add_in_port(self.i_input)
        self.add_in_port(self.i_reset)
        self.add_out_port(self.o_true)
        self.add_out_port(self.o_false)

    def initialize(self):
        self.passivate()

    def deltint(self):
        debug(f"ConditionalXor {self.name} internal transition")
        self._input = None
        self.passivate()

    def deltext(self, e):
        if self.i_reset:
            self.i_reset.empty()
            for port in self.in_ports:
                if port:
                    port.empty()
            return self.passivate()
        debug(f"ConditionalXor {self.name} external transition")
        if self.i_input:
            self._input = self.i_input.get()
            debug(f"ConditionalXor {self.name} received input: {self._input}")
            self.activate()

    @abstractmethod
    def condition(self, item: I) -> bool:
        """
        Check whether the condition is met for the given input item.

        :param item: Input item of type object to be checked.
        :return: Boolean indicating whether the condition is met.
        """
        raise NotImplementedError("Subclasses must implement the condition method.")

    def lambdaf(self):
        debug(f"ConditionalXor {self.name} output function")
        if self._input is not None:
            if self.condition(self._input):
                debug(f"ConditionalXor {self.name} condition met, outputting True")
                self.o_true.add(self._input)
            else:
                debug(f"ConditionalXor {self.name} condition not met, outputting False")
                self.o_false.add(False)

    def exit(self):
        return super().exit()


class Storage[S](Atomic):
    """
    An atomic model that stores incoming items.
    """

    def __init__(self, name=None):
        super().__init__(name)

        self.i_input = Port(object, "i_input")

        self._storage: List[S] = []
        self._item: S = None

        self.add_in_port(self.i_input)

    def initialize(self):
        self._item = None
        self.passivate()

    def deltint(self):
        debug(f"Storage {self.name} internal transition")
        self.passivate()

    def deltext(self, e):
        debug(f"Storage {self.name} external transition")
        if self.i_input:
            self._item: S = self.i_input.get()
            debug(f"Storage {self.name} received input: {self._item}")
            self.activate()

    def lambdaf(self):
        self._storage.append(self._item)

    def exit(self):
        return super().exit()

    @property
    def storage(self) -> List[S]:
        return self._storage


class ResetAll(Atomic):
    """
    An atomic to trigger resets on all other given atomics.
    """

    def __init__(self, name,):
        super().__init__(name)

        self.i_reset = Port(bool, "i_reset")
        self.add_in_port(self.i_reset)

        self.o_trigger = Port(bool, "o_trigger")
        self.add_out_port(self.o_trigger)

    def initialize(self):
        self.passivate()

    def deltint(self):
        self.passivate()

    def deltext(self, e):
        if self.i_reset:
            self.activate()

    def lambdaf(self):
        if self.i_reset:
            self.i_reset.empty()
            self.o_trigger.add(True)

    def exit(self):
        return super().exit()
    
    def add_resetables(self, model:Coupled, resetables:Collection):

        for rest in resetables:
            if hasattr(rest, "i_reset"):
                model.add_coupling(self.i_reset, rest.i_reset)
            else:
                raise ValueError(f"Given reset {rest} does not have port i_reset")