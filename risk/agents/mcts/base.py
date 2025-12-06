
from mcts.base.base import BaseAction

from abc import abstractmethod
from uuid import uuid4 as uuid


class BaseAgentAction(BaseAction):
    """
    Template for building an MCTS action.
    """

    def __init__(self, terminal: bool):
        super().__init__()
        self._terminal = terminal
        self._id = uuid()

    @property
    def id(self):
        return self._id

    @abstractmethod
    def execute(self, state):
        pass

    def is_terminal(self) -> bool:
        return self._terminal

    @abstractmethod
    def to_step(self, *args) -> object | None:
        return None

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def __eq__(self, other):
        pass

    @abstractmethod
    def __hash__(self):
        return hash(("noop"))


class NoAction(BaseAgentAction):
    """
    Represents an noop action in state exploration.
    """

    def __init__(self):
        super().__init__(True)

    def execute(self, state):
        return state
    
    def to_step(self, *args):
        return None

    def __str__(self):
        return "action-noop"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return isinstance(other, NoAction)

    def __hash__(self):
        return hash(("noop"))


def extractStatistics(searcher, action) -> dict:
    """Return simple statistics for ``action`` from ``searcher``."""
    statistics = {}
    statistics["rootNumVisits"] = searcher.root.numVisits
    statistics["rootTotalReward"] = searcher.root.totalReward
    statistics["actionNumVisits"] = searcher.root.children[action].numVisits
    statistics["actionTotalReward"] = searcher.root.children[action].totalReward
    return statistics