#!/usr/bin/env python3
"""
Simple script to run the Agent Risk pygame simulation.

Usage:
    python run_game.py [-g REGIONS] [-p PLAYERS] [-s ARMY_SIZE]

Arguments:
    -g, --regions    Number of territories/regions to generate (default: 15)
    -p, --players    Number of players in the simulation (default: 3)
    -s, --army-size  Starting army size per player (default: 20)
"""

import sys
import os
import argparse

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from risk.game import main

def parse_arguments():
    """Parse command line arguments for game parameters."""
    parser = argparse.ArgumentParser(
        description="Run the Agent Risk pygame simulation with configurable parameters.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-g', '--regions',
        type=int,
        default=15,
        help='Number of territories/regions to generate (default: 15)'
    )
    
    parser.add_argument(
        '-p', '--players',
        type=int,
        default=3,
        help='Number of players in the simulation (default: 3)'
    )
    
    parser.add_argument(
        '-s', '--army-size',
        type=int,
        default=20,
        help='Starting army size per player (default: 20)'
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # Validate arguments
    if args.regions < 1:
        print("Error: Number of regions must be at least 1", file=sys.stderr)
        sys.exit(1)
    
    if args.players < 2:
        print("Error: Number of players must be at least 2", file=sys.stderr)
        sys.exit(1)
        
    if args.army_size < 1:
        print("Error: Army size must be at least 1", file=sys.stderr)
        sys.exit(1)
    
    print(f"Starting Agent Risk simulation with {args.regions} regions, {args.players} players, {args.army_size} armies each")
    main(g=args.regions, p=args.players, s=args.army_size)