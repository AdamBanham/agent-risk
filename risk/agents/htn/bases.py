from copy import deepcopy
from risk.state.plan import Plan
from dataclasses import dataclass


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
