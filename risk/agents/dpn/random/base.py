from simpn.simulator import SimProblem, SimVar

from itertools import product
from typing import Callable


class GuardedTransition:
    """
    Helper class to make a transition in a `SimProblem`. A thin wrapper around
    the needed calls on a known problem to make a `SimEvent`.

    ---
    Usage
    ---
    Create a new class definition that inherits from this class with the
    following fields. After the defintion is created a new prototype instance
    will be recorded in the simulation problem.

    ^^^^
    Required class fields
    ^^^^
    :fieldname `model`:
        The `SimProblem` to add the prototype to.
    :fieldname `name`:
        A unique identifier for the new prototype.
    :fieldname `outgoing`:
        A list of `SimVar` or `str` to pull tokens from to trigger the task.
        If a `str` is passed, the place will be looked up or made beforehand.
    :fieldname `outgoing`:
        A list of `SimVar` or `str` to place tokens into from the behaviour
        function.
        If a `str` is passed, the place will be looked up or made beforehand.
    :fieldname `guard`:
        A function taking a possible binding from `incoming` and returning
        a boolean indicating if the transition is allowed to fire.

    ^^^
    Required class functions
    ^^^
    :fieldname `behaviour`:
        A function taking tokens from `incoming` and returns a list of tokens
        to place into `outgoing`.

    ^^^
    Example usage
    ^^^

    .. code-block :: python
        class Drive(Transition):
            name="Drive"
            model=problem
            incoming=["Home"]
            outgoing=["Work"]

            def behaviour(h):
                return [SimToken(h, delay=5)]
    """

    model: SimProblem = None
    name = None
    incoming = None
    outgoing = None

    @staticmethod
    def __create__(cls, **kwargs):
        if any(
            hasattr(cls, attr) and getattr(cls, attr) is None
            for attr in ["name", "model", "incoming", "outgoing"]
        ):
            raise ValueError(
                'Missing values for the following key attributes: ["name","model","incoming", "outgoing"]'
            )
        incoming = []
        for inc in cls.incoming:
            if isinstance(inc, str):
                try:
                    inc = cls.model.var(inc)
                except Exception as e:
                    inc = cls.model.add_var(inc)
                finally:
                    incoming.append(inc)
            elif isinstance(inc, SimVar):
                incoming.append(inc)
            else:
                raise ValueError(
                    f"Unknown type provided in incoming :: {inc=}, of {type(inc)=}"
                )
        outgoing = []
        for inc in cls.outgoing:
            if isinstance(inc, str):
                try:
                    inc = cls.model.var(inc)
                except Exception as e:
                    inc = cls.model.add_var(inc)
                finally:
                    outgoing.append(inc)
            elif isinstance(inc, SimVar):
                outgoing.append(inc)
            else:
                raise ValueError(
                    f"Unknown type provided in outgoing :: {inc=}, of {type(inc)=}"
                )
        if not hasattr(cls, "behaviour"):
            raise ValueError("Missing behaviour function on class.")
        if not hasattr(cls, "guard"):
            raise ValueError("Missing guard function on class.")
        behaviour = cls.behaviour
        name = cls.name
        guard = cls.guard
        cls.model.add_event(incoming, outgoing, behaviour, name, guard)

    def __init_subclass__(cls, **kwargs):
        if any(
            hasattr(cls, attr) and getattr(cls, attr) is None
            for attr in ["name", "model", "incoming", "outgoing"]
        ):
            raise ValueError(
                'Missing values for the following key attributes: ["name","model","incoming", "outgoing"]'
            )
        incoming = []
        for inc in cls.incoming:
            if isinstance(inc, str):
                try:
                    inc = cls.model.var(inc)
                except Exception as e:
                    inc = cls.model.add_var(inc)
                finally:
                    incoming.append(inc)
            elif isinstance(inc, SimVar):
                incoming.append(inc)
            else:
                raise ValueError(
                    f"Unknown type provided in incoming :: {inc=}, of {type(inc)=}"
                )
        outgoing = []
        for inc in cls.outgoing:
            if isinstance(inc, str):
                try:
                    inc = cls.model.var(inc)
                except Exception as e:
                    inc = cls.model.add_var(inc)
                finally:
                    outgoing.append(inc)
            elif isinstance(inc, SimVar):
                outgoing.append(inc)
            else:
                raise ValueError(
                    f"Unknown type provided in outgoing :: {inc=}, of {type(inc)=}"
                )
        if not hasattr(cls, "behaviour"):
            raise ValueError("Missing behaviour function on class.")
        if not hasattr(cls, "guard"):
            raise ValueError("Missing guard function on class.")
        behaviour = cls.behaviour
        name = cls.name
        guard = cls.guard
        cls.model.add_event(incoming, outgoing, behaviour, name, guard)


class ExpressiveSimProblem(SimProblem):
    """
    A SimProblem variant that supports generating all possible
    bindings.
    """

    def _construct_binding(self, incoming, indices, guard: Callable = None):
        binding = []
        max_token_time = 0
        parameters = []
        for i in range(len(incoming)):
            place = incoming[i]
            token = place.marking[indices[i]]
            binding.append((place, token))
            parameters.append(token.value)
            if token.time > max_token_time:
                max_token_time = token.time
        if guard is not None and not guard(*parameters):
            return None
        return (binding, max_token_time)

    def event_bindings(self, event):
        incoming = event.incoming

        produce = True
        for place in incoming:
            if len(place.marking) == 0:
                produce = False
                break

        if not produce:
            return []

        all_indices = list(
            product(*[list(range(len(place.marking))) for place in incoming])
        )
        return [self._construct_binding(incoming, indices, event.guard) for indices in all_indices]

    def bindings(self):
        timed_bindings = []
        min_enabling_time = None
        for t in self.events:
            bindings = self.event_bindings(t)
            for timed_binding in bindings:
                if timed_binding is not None:
                    (binding, time) = timed_binding
                    timed_bindings.append((binding, time, t))
                    if min_enabling_time is None or time < min_enabling_time:
                        min_enabling_time = time
        # timed bindings are only enabled if they have time <= clock
        # if there are no such bindings, set the clock to the earliest time
        # at which there are
        if min_enabling_time is not None and min_enabling_time > self.clock:
            self.clock = min_enabling_time

        # now return the untimed bindings + the timed bindings that have
        # time <= clock
        return [
            (binding, self.clock, t)
            for (binding, time, t) in timed_bindings
            if time <= self.clock
        ]
