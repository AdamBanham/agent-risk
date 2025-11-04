from .simple import RandomAgent
from .bt.random import BTRandomAgent
from .htn.random import HTNRandomAgent
from .mcts.random import MCSTRandomAgent
from .dpn.random import DPNRandomAgent


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


class HTNAgents(AgentFamily):

    class TYPES(Enum):
        RANDOM = HTNRandomAgent

    @staticmethod
    def get_agent(strategy: AgentStrategies):
        for agent in HTNAgents.TYPES:
            if agent.name == strategy.name:
                return agent.value
        raise ValueError(f"Unknown strategy: {strategy}")


class MCTSAgents(AgentFamily):

    class TYPES(Enum):
        RANDOM = MCSTRandomAgent

    @staticmethod
    def get_agent(strategy: AgentStrategies):
        for agent in MCTSAgents.TYPES:
            if agent.name == strategy.name:
                return agent.value
        raise ValueError(f"Unknown strategy: {strategy}")


class DPNAgents(AgentFamily):

    class TYPES(Enum):
        RANDOM = DPNRandomAgent

    @staticmethod
    def get_agent(strategy: AgentStrategies):
        for agent in DPNAgents.TYPES:
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
    SIMPLE = ("simple", RandomAgents)
    BEHAVIOR_TREE = ("bt", BTAgents)
    HIERARCHICAL_TASK_NETWORK = ("htn", HTNAgents)
    MONTE_CARLO_TREE_SEARCH = ("mcts", MCTSAgents)
    DATA_PETRI_NET = ("dpn", DPNAgents)

    @staticmethod
    def get_selector(type: str) -> AgentFamily:
        for agent_type in AgentTypes:
            if agent_type.value[0] == type:
                return agent_type.value[1]
        raise ValueError(f"Unknown agent type: {type}")


if __name__ == "__main__":

    # Example usage
    agent_family = AgentTypes.get_selector("dpn")
    agent_class = agent_family.get_agent(AgentStrategies.RANDOM)
    agent = agent_class(player_id=1)
    print(f"Created agent: {agent.name}")
