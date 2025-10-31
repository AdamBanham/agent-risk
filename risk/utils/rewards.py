from risk.state.game_state import GameState


def calculate_player_position_rewards(game_state: GameState) -> dict:
    """
    Calculate rewards for each player based on their current position in the game.
    Players with more territories and armies receive higher rewards.

    Args:
        game_state (GameState): The current state of the game.

    Returns:
        dict: A dictionary mapping player IDs to their calculated rewards.
    """
    total_territories = game_state.regions
    player_armies = [p.total_armies for p in game_state.players.values()]
    total_armies = sum(player_armies)
    rewards = {}

    for player_id in range(game_state.num_players):
        territories = len(game_state.get_territories_owned_by(player_id))
        armies = player_armies[player_id]

        territory_ratio = (
            territories / total_territories if total_territories > 0 else 0
        )
        army_ratio = armies / total_armies if total_armies > 0 else 0

        # Simple reward calculation: weighted sum of territory and army ratios
        reward = (0.5 * territory_ratio) + (0.5 * army_ratio)
        rewards[player_id] = reward

    return rewards
