from os import path
import json
import argparse
import re

from run_eval import create_options

def parse_args() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="This runner collections digonstoic information about" \
        " agents and their plans from an evaluation set.",
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
        help="Whether to collect rejected events from the eval runs.",
    )

    return parser.parse_args()

CONFIG_FILE = "combo_{id:04d}.config"
STACK_FILE = "combo_{id:04d}_{perm}.stack"

REJECT_MATCH = "reject-(.*?)-.*P({id}).*?:(.*?),"

REASON_SWAPS = {
    'T1' : 'cannot attack your own territory',
    'T2' : 'not enough troops to attack',
    'T3' : 'you do not own the attacking territory',
    'T4' : 'must leave at least one troop behind',
    'T5' : 'not enough troops to transfer'
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

STRATS = {
    "rand.": "random",
    "def.": "defensive",
    "agg.": "aggressive",
}

TABLE_PREFIX = """\\begin{table}[tb]
    \\centering
    \\caption{
        Breakdown of rejected events across simulation runs.
    }
    \\label{tab:eval:rejected}
    \\begin{tabular}{ll|c|ccc|c}
        \\toprule 
         & Strat.     & place & \\multicolumn{3}{c|}{attack} & move  \\\\
         &            &       &    T1   &    T2    &  T3   &       \\\\
        \\midrule"""

TABLE_CONTENT = """
        Base & \\\\
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
        DEVS & \\\\
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
        BT  &  \\\\
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
        HTN & \\\\  
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
        MCTS & \\\\
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
        BPMN & \\\\
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
        DPN & \\\\
             & rand.  &{}&{}&{}&{}&{}\\\\
             & def.   &{}&{}&{}&{}&{}\\\\
             & agg.   &{}&{}&{}&{}&{}\\\\
"""

TABLE_SUFFIX = """  \\end{tabular}
\\end{table}"""


def format_count(length: int, count:int) -> str:
    clen = len(str(count))
    if clen < length:
        surrounding = (length - clen)
        if surrounding % 2 == 0:
            return " " * (surrounding // 2) + str(count) + " " * (surrounding // 2)
        else:
            return " " * (surrounding // 2) + str(count) + " " * (surrounding // 2 + 1)
    else:
        return str(count)
    
def work():

    # arg parse and create initial reporting structure
    args = parse_args()
    options = create_options()
    rejected = dict(
        (key, dict(
            (strat, {
                "placement" : {}, "attack" : {}, "transfer" : {}
            })
            for strat 
            in strats
        ))
        for key, strats 
        in options.items()
    )

    # loop through all config files in the eval path
    if args.collect:
        id = 0
        while path.exists(path.join(args.path, CONFIG_FILE.format(id=id))):
            config = json.load(open(path.join(args.path, CONFIG_FILE.format(id=id))))
            for perm in range(7):
                stack = open(path.join(args.path, STACK_FILE.format(id=id, perm=perm)), "r").read()

                # for each player, check their config and then collect rejects
                for player in range(7):
                    player_config =  config[str(player)]
                    reject_results = rejected[player_config["type"]][player_config["strat"]]

                    matcher = re.compile(
                        REJECT_MATCH.format(id=player),
                        flags=re.I | re.M
                    )
                    matching = re.findall(matcher, stack)
                    if matching:
                        for (type, mplayer, reason) in matching:
                            try :
                                type = type.lower().strip()
                                reason = reason.lower().strip()
                                if reason not in reject_results[type]:
                                    reject_results[type][reason] = 0
                                reject_results[type][reason] += 1
                            except Exception as e:
                                print(f"Could not process rejection match {type} {mplayer} {reason}: {e}")
                                raise e

            id += 1

            if (id+1) % 25 == 0:
                print(f"Processed {id+1} configurations...")

        # save collected rejections and store them in eval path
        print(f"Completed processing {id+1} configurations.")
        print(json.dumps(rejected, indent=4))

        with open(path.join(args.path, "rejected_collection.json"), "w") as f:
            f.write(json.dumps(rejected, indent=4))

        # collect all reasons seen
        seen_attack_reasons = set()
        seen_placement_reasons = set()
        seen_transfer_reasons = set()
        for agent_type, strat_data in rejected.items():
            for strat, reject_data in strat_data.items():
                for reason in reject_data["placement"].keys():
                    seen_placement_reasons.add(reason)
                for reason in reject_data["attack"].keys():
                    seen_attack_reasons.add(reason)
                for reason in reject_data["transfer"].keys():
                    seen_transfer_reasons.add(reason)
        
        print("Placement Rejection Reasons:", seen_placement_reasons)
        print("Attack Rejection Reasons:", seen_attack_reasons)
        print("Transfer Rejection Reasons:", seen_transfer_reasons)
    else:
        # load collected rejections
        print("Attempting to load collected rejections...")
        rejected = json.load(open(path.join(args.path, "rejected_collection.json")))
        print("Loaded rejection results::")
        print(json.dumps(rejected, indent=4))

    # write results
    print("Writing rejection table...")
    with open(path.join(".", "rejects.tex"), "w") as f:
        f.write(TABLE_PREFIX)

        # handle the content body
        ret = "\n"
        curr = None
        for line in TABLE_CONTENT.splitlines()[1:]:
            if len(line.split("&")) == 2:
                ret += line + "\n"
                notation = line.split("&")[0].strip()
                curr = NOTATIONS[notation]
            else:
                strat = line.split("&")[1].strip()
                strat = STRATS[strat]
                sum_of_placements = sum(rejected[curr][strat]["placement"].values())
                sum_of_transfers = sum(rejected[curr][strat]["transfer"].values())

                attack_t1 = rejected[curr][strat]["attack"].get(REASON_SWAPS["T1"], 0)
                attack_t2 = rejected[curr][strat]["attack"].get(REASON_SWAPS["T2"], 0)
                attack_t3 = rejected[curr][strat]["attack"].get(REASON_SWAPS["T3"], 0)

                ret += line.format(
                    format_count(8, sum_of_placements),
                    format_count(8, attack_t1),
                    format_count(8, attack_t2),
                    format_count(8, attack_t3),
                    format_count(8, sum_of_transfers)
                ) + "\n"

        f.write(ret)

        f.write(TABLE_SUFFIX)

    print("Wrote rejection table to rejects.tex")

if __name__ == "__main__":
    work()