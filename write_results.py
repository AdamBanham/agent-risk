import argparse
import json
from os import path

from typing import Dict
import math

TEMPLATE = """
        Base & \\\\
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
        DEVS & \\\\
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
        BT  &  \\\\
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
        HTN & \\\\
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
        MCTS & \\\\
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
        BPMN & \\\\ 
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
        DPN & \\\\
             & rand.  & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & def.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
             & agg.   & {elements} & {cc} & {runtime} ($\\pm{}{r_std}$) & {score} ($\\pm{}{s_std}$) \\\\ 
"""

ELEMENTS = {
    "simple": {"random": "n/a", "defensive": "n/a", "aggressive": "n/a"},
    "devs": {"random": "16", "defensive": "32", "aggressive": "32"},
    "bt": {"random": "30", "defensive": "35", "aggressive": "49"},
    "htn": {"random": "25", "defensive": "30", "aggressive": "34"},
    "mcts": {"random": "6", "defensive": "8", "aggressive": "8"},
    "bpmn": {"random": "24", "defensive": "32", "aggressive": "28"},
    "dpn": {"random": "10", "defensive": "14", "aggressive": "16"},
}

CC = {
    "simple": {"random": "4.4", "defensive": "6.6", "aggressive": "7.0"},
    "devs": {"random": "2.06", "defensive": "2.10", "aggressive": "2.21"},
    "bt": {"random": "1.71", "defensive": "1.81", "aggressive": "1.91"},
    "htn": {"random": "2.13", "defensive": "2.50", "aggressive": "2.20"},
    "mcts": {"random": "2.29", "defensive": "2.16", "aggressive": "2.25"},
    "bpmn": {"random": "3.17", "defensive": "2.35", "aggressive": "2.45"},
    "dpn": {"random": "3.52", "defensive": "3.05", "aggressive": "2.96"},
}

NOTATIONS = {
    "Base": "simple",
    "DEVS": "devs",
    "BT": "bt",
    "HTN": "htn",
    "MCTS": "mcts",
    "BPMN": "bpmn",
    "DPN": "dpn",
}

PATTERNS = ["random", "defensive", "aggressive"]

PREFIX = """\\begin{table}[t]
    \\centering
    \\caption{
        ##CAPTION
    }
    \\label{tab:eval:results}
    \\begin{tabular}{ll|cccc}
        \\toprule 
         & Strat. & \\# & Comp. & Run. (std) & Score (std)  \\\\
        \\midrule"""
CAPTION = """Experimentation Results, currently reporting a demonstrative run 
        over 100 turns with {combos} combinations, taking a wall time of {total} hours, 
        averaging {average} minutes per simulation."""
SUFFIX = """    \\end{tabular}
\\end{table}"""


def parse_arguments():
    """Parse command line arguments for writing the evaluation table ."""
    parser = argparse.ArgumentParser(
        description="Formats the summary of an evaluation into a LaTeX table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="The path to the evaluation folder. This should be"
        " the root of the directory",
    )

    parser.add_argument(
        "--collect",
        action="store_true",
        help="Recompute the summary statistics rather than trusting summary.json"
    )

    return parser.parse_args()


DEFAULT_SIM_RUNS = 2187
SCORE_FILE = "combo_{run:04d}.scores"
CONFIG_FILE = "combo_{run:04d}.config"
SCORING_NAME = "player{id}-{family}-{strat}"


def compute_summary(eval_path: str) -> Dict:

    summary_dict = dict(
        (family, dict(
            (strat, {
                "runtime" : [],
                "score" : []
            })
            for strat 
            in PATTERNS
        ))
        for family 
        in NOTATIONS.values()
    )

    for sim_run in range(DEFAULT_SIM_RUNS):

        if not path.exists(path.join(eval_path, CONFIG_FILE.format(run=sim_run))):
            continue

        sim_config = json.load(open( 
            path.join(eval_path, CONFIG_FILE.format(run=sim_run))
        ))
        sim_scores = json.load(open(
            path.join(eval_path, SCORE_FILE.format(run=sim_run))
        ))

        for player in range(7):
            family = sim_config[str(player)]["type"]
            strat = sim_config[str(player)]["strat"]

            scoring = sim_scores[SCORING_NAME.format(
                id=player, family=family, strat=strat
            )]

            summary_dict[family][strat]["runtime"].append(scoring["runtime"])
            summary_dict[family][strat]["score"].append(scoring["score"])

        if sim_run % 10 == 0:
            print(f"processed {sim_run+1}/{DEFAULT_SIM_RUNS+1}...")

    condensed_stats = {}
    for family in summary_dict.keys():
        condensed_stats[family] = {}
        for strat in summary_dict[family].keys():
            runtimes = summary_dict[family][strat]["runtime"]
            r_mean = sum(runtimes) / len(runtimes) if len(runtimes) > 0 else 0
            r_var = sum((x - r_mean) ** 2 for x in runtimes) / len(runtimes) if len(runtimes) > 0 else 0
            scores = summary_dict[family][strat]["score"]
            s_mean = sum(scores) / len(scores) if len(scores) > 0 else 0
            s_var = sum((x - s_mean) ** 2 for x in scores) / len(scores) if len(scores) > 0 else 0
            condensed_stats[family][strat] = {
                "std_runtime": math.sqrt(r_var),
                "avg_runtime": r_mean,
                "std_score": math.sqrt(s_var),
                "avg_score": s_mean,
            }

    return condensed_stats


if __name__ == "__main__":

    args = parse_arguments()

    if not path.exists(args.path):
        raise ValueError("Could not find the path to the given evaluation dir.")

    summary_path = path.join(args.path, "summary.json")
    if path.exists(summary_path):
        all_data = json.load(open(summary_path))
    else:
        print("Unable to find summary.json, using dummy data for the timing of replications.")
        all_data = {
            "total_simulations": DEFAULT_SIM_RUNS,
            "total_time": 1,
            "individual_times": [1],
            "detailed_stats": {}
        }
    if args.collect:
        # recompute summary data 
        summary_data = compute_summary(args.path)
        print("Recomputed summary data...")
    else:
        # use existing summary data instead
        if not path.exists(summary_path):
            raise ValueError("Unable to find the summary.json in evaluation dir.")

        summary_data = all_data["detailed_stats"]

    ret = "\n"
    curr = None
    pattern = None
    for line in TEMPLATE.splitlines()[1:]:
        if len(line.split("&")) == 2:
            ret += line + "\n"
            notation = line.split("&")[0].strip()
            curr = NOTATIONS[notation]
            pattern = 0
        else:
            p_type = PATTERNS[pattern]
            if p_type in summary_data[curr]:
                data = summary_data[curr][p_type]
                line = line.replace("{}", "{{}}")
                line = line.format(
                    elements=ELEMENTS[curr][p_type],
                    cc=CC[curr][p_type],
                    runtime=f"{data["avg_runtime"]:.2f}",
                    r_std=f"{data["std_runtime"]:.2f}",
                    score=f"{data["avg_score"]:.2f}",
                    s_std=f"{data["std_score"]:.2f}",
                )
            else:
                line = line.replace("{}", "{{}}")
                line = line.format(
                    elements="?", cc="?", runtime="?", r_std="?", score="?", s_std="?"
                )
            ret += line + "\n"
            pattern += 1

    prefix = PREFIX
    avg = sum(all_data["individual_times"])
    avg = avg / len(all_data["individual_times"])
    caption = CAPTION.format(
        combos=all_data["total_simulations"],
        total=f"{all_data["total_time"]/(60 * 60):.2f}",
        average=f"{avg/60:.2f}",
    )
    prefix = prefix.replace("##CAPTION", caption)

    with open(path.join(".", "results.tex"), "w") as f:
        f.write(prefix)
        f.write(ret)
        f.write(SUFFIX)

    print("Written resulting evaluation to ./results.tex")
