from risk.engine.controller import SimulationController
from risk.state.event_stack.events import (
    PlayingEvent,
    AgentTurnEndEvent,
    AttackPhase,
    AttackPhaseEndEvent,
    MovementPhase,
    MovementPhaseEndEvent,
    PlacementPhase,
    PlacementPhaseEndEvent,
    GameEvent,
)
from risk.state.game_state import GameState
from .base import Engine, RecordStackEngine
from .turns import (
    RiskGameEngine,
    RiskTurnEngine,
    RiskPlacementEngine,
    RiskAttackEngine,
    RiskMovementEngine,
)

RISK_ENGINES = [
    RiskGameEngine(),
    RiskTurnEngine(),
    RiskPlacementEngine(),
    RiskAttackEngine(),
    RiskMovementEngine(),
]


from risk.state.event_stack import AgentTurnPhase, Event
from risk.state.event_stack import SystemInterruptEvent
from typing import List, Optional


class RiskForwardEngine(Engine):
    """
    An engine halts the simulation after processing up to N
    turns.
    """

    allowed_elements = [AgentTurnPhase]

    def __init__(self, max_turns: int, starting_turn: int = 0):
        super().__init__("Risk Forward Simulation Engine")
        self.max = max_turns
        self.start = starting_turn

    def process(self, state: GameState, element) -> Optional[List[Event]]:
        if state.current_turn >= self.start + self.max:
            return [SystemInterruptEvent()]
        return super().process(state, element)


class RiskRecordEngine(RecordStackEngine):
    """
    An engine that records specific event for replay later.
    Creates a readable level depth level based on the pairs
    of levels seen on the event stack.
    """

    def __init__(self):
        super().__init__(
            pairs=[
                (PlayingEvent, AgentTurnEndEvent),
                (PlacementPhase, PlacementPhaseEndEvent),
                (AttackPhase, AttackPhaseEndEvent),
                (MovementPhase, MovementPhaseEndEvent),
            ]
        )


from risk.utils.rewards import calculate_player_position_rewards


class RiskPlayerScoresEngine(Engine):
    """
    An engine that tracks player scores over time.
    """

    allowed_elements = [AgentTurnEndEvent]

    def __init__(self, players: int):
        super().__init__("Risk Player Scores Engine")
        self.scores = {player_id: [] for player_id in range(players)}
        self._agent_turn = 0

    def process(self, state: GameState, element: Event) -> Optional[List[Event]]:
        rewards = calculate_player_position_rewards(state)
        turn = state.current_turn
        alive = sum(1 for p in state.players.values() if p.is_active)
        self._agent_turn += 1
        time = turn + self._agent_turn / alive
        if self._agent_turn >= alive:
            self._agent_turn = 0
        for player_id, reward in rewards.items():
            self.scores[player_id].append((time, reward))
        return super().process(state, element)

    def plot_scores(self):
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(10, 6))
        axes = fig.subplots(1, 2)

        totals = self.get_total_scores()

        colours =  [
                (200, 50, 50),  # Red
                (50, 200, 50),  # Green
                (50, 50, 200),  # Blue
                (200, 200, 50),  # Yellow
                (200, 50, 200),  # Magenta
                (50, 200, 200),  # Cyan
                (150, 75, 0),  # Brown
                (255, 165, 0),  # Orange
        ]

        for (player_id, score_history), colour in zip(self.scores.items(), colours):
            sorted_history = sorted(score_history, key=lambda x: x[0])
            turns, scores = zip(*sorted_history)
            # smooth scores
            window_size = 3
            if len(scores) >= window_size:
                smoothed_scores = []
                for i in range(len(scores)):
                    window = scores[max(0, i - window_size + 1):i + 1]
                    smoothed_scores.append(sum(window) / len(window))
                scores = smoothed_scores
            axes[0].plot(
                turns,
                scores,
                c=[colour[0]/255, colour[1]/255, colour[2]/255],
                label=f"Player {player_id} (Total: {totals[player_id]:.2f})",
            )
        axes[0].grid(True)
        axes[0].set_xlabel("agent-turns")
        axes[0].set_xlim(left=0)
        axes[0].set_ylabel("Score")
        axes[0].set_ylim(0, 1)
        axes[0].set_title("Player Scores Over Time")
        axes[0].legend()

        # plot the cummulative scores as a line chart
        for (player_id, score_history), colour in zip(self.scores.items(), colours):
            sorted_history = sorted(score_history, key=lambda x: x[0])
            turns, scores = zip(*sorted_history)
            # calculate cumulative sum
            cumulative_scores = []
            running_sum = 0
            for score in scores:
                running_sum += score
                cumulative_scores.append(running_sum)
            axes[1].plot(
                turns,
                cumulative_scores,
                c=[colour[0]/255, colour[1]/255, colour[2]/255],
                label=f"Player {player_id} (Total: {totals[player_id]:.2f})",
            )
        axes[1].grid(True)
        axes[1].set_xlabel("agent-turns")
        axes[1].set_xlim(left=0)
        axes[1].set_ylabel("Cumulative Score")
        axes[1].set_ylim(bottom=0)
        axes[1].set_title("Cumulative Player Scores Over Time")
        axes[1].legend()

        plt.show()

    def get_total_scores(self):
        total = {}
        for player_id, score_history in self.scores.items():
            if any(score == 0 for _, score in score_history):
                total[player_id] = 0
            else:
                total[player_id] = sum(score for _, score in score_history)
        return total


class RiskSimulationController(SimulationController):
    """
    The controller responsible for managing the event stack
    and engine processing loop for the Risk simulation.
    """

    def __init__(self, game_state: GameState):
        super().__init__(game_state, RISK_ENGINES)
        self.tape = RiskRecordEngine()
        self.add_engine(self.tape)
        self.event_stack.push(GameEvent())
