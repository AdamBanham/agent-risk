from risk.state.game_state import GameState
from risk.utils.replay import simulate_turns, SimulationConfiguration

from matplotlib import pyplot as plt

import argparse
from os.path import join


def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Run the Agent Risk pygame simulation with AI agents from a known state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-s",
        "--state",
        type=str,
        default="test.state",
        help="Path to the state file to load (default: test.state)",
    )

    parser.add_argument(
        "--ai-delay",
        type=float,
        default=0.1,
        help="Delay between AI actions in seconds (default: 0.1)",
    )

    parser.add_argument(
        "--attack-rate",
        type=float,
        default=0.85,
        help="AI attack probability 0.0-1.0 (default: 0.85)",
    )

    parser.add_argument(
        "--sim-delay",
        type=float,
        default=0.2,
        help="Delay between simulation steps in seconds (default: 0.2)",
    )

    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of turns to simulate forward (default: 10)",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of simulation runs to perform (default: 10)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    from risk.utils.logging import setLevel, info
    from logging import INFO
    from json import load

    setLevel(INFO)

    test_state = GameState.create_new_game(200, 8, 200)
    test_state.initialise()

    def get_name(info):
        return f"{info['type']}-{info['strat']}"

    ai_config = load(open("ai.config", "r"))
    total_scores = dict((int(player_id), []) for player_id in ai_config.keys())
    scores = dict((int(player_id), []) for player_id in ai_config.keys())
    names = dict(
        (int(player_id), get_name(ai_config[player_id]))
        for player_id in ai_config.keys()
    )

    try:
        for run in range(args.runs):
            _, _, scorer = simulate_turns(
                test_state,
                args.turns,
                SimulationConfiguration(
                    attack_rate=args.attack_rate, load_ai_from_file=True, score=True
                ),
            )

            info(f"[RUN {run+1:04d}] Final Scores:")
            for player_id, score in scorer.get_total_scores().items():
                info(f"Player {player_id}: {score} points")
                total_scores[player_id].append(score)
                scores[player_id].extend([tick[1] for tick in scorer.scores[player_id]])
    finally:

        info("\nAverage Scores over runs:")
        for player_id, score_list in scores.items():
            average_score = sum(score_list) / len(score_list)
            info(f"Player {player_id} running score avg: {average_score:.2f}%")
        info("\nOverall Average Scores per turn:")
        for player_id, score_list in total_scores.items():
            average_score = sum(score_list) / len(score_list)
            info(f"Player {player_id} overall score avg: {average_score:.2f} points")

        fig = plt.figure(figsize=(10, 6))

        colours = [
            (200, 50, 50),  # Red
            (50, 200, 50),  # Green
            (50, 50, 200),  # Blue
            (200, 200, 50),  # Yellow
            (200, 50, 200),  # Magenta
            (50, 200, 200),  # Cyan
            (150, 75, 0),  # Brown
            (255, 165, 0),  # Orange
        ]

        axes = fig.subplots(1, 2)
        for player_id, score_list in scores.items():
            axes[0].hist(
                score_list,
                bins=100,
                alpha=0.5,
                color=[
                    colours[player_id][0] / 255,
                    colours[player_id][1] / 255,
                    colours[player_id][2] / 255,
                ],
                label=f"P-{player_id}-{names[player_id]}",
            )
        for player_id, score_list in total_scores.items():
            axes[1].hist(
                score_list,
                bins=25,
                alpha=0.5,
                color=[
                    colours[player_id][0] / 255,
                    colours[player_id][1] / 255,
                    colours[player_id][2] / 255,
                ],
                label=f"P-{player_id}-{names[player_id]}",
            )

        axes[0].set_title("Distribution of Player Scores Over Time")
        axes[0].set_xlabel("Score (%)")
        axes[0].set_ylabel("Frequency")
        axes[0].set_xlim(0, 1)
        axes[0].legend()
        axes[1].set_title("Distribution of Total Player Scores")
        axes[1].set_xlabel("Total Score (points)")
        axes[1].set_ylabel("Frequency")
        axes[1].set_xlim(left=0)
        axes[1].legend()
        plt.show()

        fig.savefig(
            join(
                ".",
                "out",
                "score_distributions_T{}_R{}.png".format(args.turns, args.runs),
            ),
            dpi=300,
        )
