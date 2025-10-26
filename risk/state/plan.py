"""
This module introduces the concept of a plan and how it
is represented on the simulation event stack.
"""

from typing import Union

from .game_state import GameState


class Goal:
    """
    A goal to be achieved by the agent.
    """

    def __init__(self, description: str):
        self.description = description

    def achieved(self, state: GameState, plan: "Plan") -> bool:
        """
        Check if the goal has been achieved in the given state.
        """
        return False

    def __str__(self) -> str:
        return f"Goal: {self.description}"

    def __repr__(self) -> str:
        return f"Goal({repr(self.description)})"

    def __hash__(self):
        return hash(self.description)

    def __eq__(self, other):
        if not isinstance(other, Goal):
            return False
        return self.description == other.description


class Plan:
    """
    A sequence of aggregated behaviour that achieves how to
    achieve a goal.
    """

    def __init__(self, name: str, goal: Goal):
        self.name = name
        self.goal = goal
        self.steps = []

    def add_step(self, step: "Step") -> "Plan":
        """
        Add a step to the plan.
        """
        self.steps.append(step)
        return self

    def add_steps(self, steps: list["Step"]) -> "Plan":
        """
        Add multiple steps to the plan.
        """
        self.steps.extend(steps)
        return self

    def peek_step(self) -> Union[None, "Step"]:
        """
        Peek at the next step in the plan.
        """
        if self.steps:
            return self.steps[0]
        return None

    def pop_step(self) -> Union[None, "Step"]:
        """
        Pop the next step off the plan.
        """
        if len(self.steps) > 0:
            return self.steps.pop(0)
        return None

    def goal_achieved(self, state: GameState) -> bool:
        """
        Check if the plan's goal has been achieved in the given state.
        """
        return self.goal.achieved(state, self)

    def is_done(self) -> bool:
        """
        Check if the plan has no more steps.
        """
        return len(self) == 0

    def __len__(self) -> int:
        return len(self.steps)

    def __str__(self) -> str:
        return f"Plan({self.name}, Goal: {self.goal.description}, Steps: {len(self)})"

    def __repr__(self) -> str:
        ret = f"Plan({repr(self.name)}, goal={repr(self.goal)})"
        ret += f".add_steps({repr(self.steps)})"
        return ret

    def __hash__(self):
        return hash((self.name, self.goal, tuple(self.steps)))

    def __eq__(self, other):
        if not isinstance(other, Plan):
            return False
        return (
            self.name == other.name
            and self.goal == other.goal
            and self.steps == other.steps
        )


class Step:
    """
    A single step in a plan.
    """

    def __init__(self, description: str):
        self.description = description

    def execute(self, state: GameState) -> Union[GameState, None, Plan]:
        """
        Execute the step and return either a new state
        (will be changed to some mutator event),
        None is the step requires no further action,
        or a new plan to be executed to complete this step.
        """
        return None

    def __str__(self) -> str:
        return f"Step: {self.description}"

    def __repr__(self) -> str:
        return f"Step({repr(self.description)})"

    def __hash__(self):
        return hash(self.description)

    def __eq__(self, other):
        if not isinstance(other, Step):
            return False
        return self.description == other.description
