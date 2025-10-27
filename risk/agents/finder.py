from .simple import RandomAgent
from .bt.random import BTRandomAgent

from enum import Enum
from .agent import BaseAgent
from typing import Protocol
from abc import abstractmethod


class AgentStrategies(Enum):
    RANDOM = "random"
    DEFENSIVE = "defensive"
    AGGRESSIVE = "aggressive"

    @staticmethod
    def find(strategy: str):
        for strat in AgentStrategies:
            if strat.value == strategy:
                return strat
        raise ValueError(f"Unknown strategy: {strategy}")


class AgentFamily(Protocol):

    @staticmethod
    @abstractmethod
    def get_agent(strategy: AgentStrategies) -> BaseAgent:
        pass


class BTAgents(AgentFamily):

    class TYPES(Enum):
        RANDOM = BTRandomAgent

    @staticmethod
    def get_agent(strategy: AgentStrategies):
        for agent in BTAgents.TYPES:
            if agent.name == strategy.name:
                return agent.value
        raise ValueError(f"Unknown strategy: {strategy}")


class RandomAgents(AgentFamily):

    class TYPES(Enum):
        RANDOM = RandomAgent

    @staticmethod
    def get_agent(strategy: AgentStrategies):
        for agent in RandomAgents.TYPES:
            if agent.name == strategy.name:
                return agent.value
        raise ValueError(f"Unknown strategy: {strategy}")


class AgentTypes(Enum):
    SIMPLE = "simple"
    BEHAVIOR_TREE = "bt"

    @staticmethod
    def get_selector(type: str) -> AgentFamily:
        if type == AgentTypes.SIMPLE.value:
            return RandomAgents
        elif type == AgentTypes.BEHAVIOR_TREE.value:
            return BTAgents
        else:
            raise ValueError(f"Unknown agent type: {type}")
