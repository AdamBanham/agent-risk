from simpn.simulator import SimProblem

from itertools import product
from typing import Callable


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
