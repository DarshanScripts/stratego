import time
import argparse
from stratego.env.stratego_env import StrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines
from stratego.utils.move_processor import process_move
from stratego.game_logger import GameLogger
from stratego.game_analyzer import analyze_and_update_prompt


def build_agent(spec: str, prompt_name: str):
    """Build an agent from specification string like 'ollama:mistral:7b'."""
    kind, name = spec.split(":", 1)
    if kind == "ollama":
        return OllamaAgent(model_name=name, temperature=0.2, num_predict=32,
                           prompt_pack=get_prompt_pack(prompt_name))
    raise ValueError(f"Unknown agent spec: {spec}")

def print_board(observation: str):
    """Print the board from observation text."""
    block = extract_board_block_lines(observation)
    if block:
        print("\n".join(block))

# With those arguments, user can change game setting
def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:phi3:3.8b")
    p.add_argument("--p1", default="ollama:gemma3:1b")
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--env_id", default="Stratego-v0", help="TextArena environment id")
    p.add_argument("--log-dir", default="logs", help="Directory for per-game CSV logs")
    p.add_argument("--game-id", default=None, help="Optional custom game id in CSV filename")
    args = p.parse_args()

    agents = {
        0: build_agent(args.p0, args.prompt),
        1: build_agent(args.p1, args.prompt),
    }
    env = StrategoEnv(env_id=args.env_id)
    env.reset(num_players=2)
    
    # Track game start time
    game_start_time = time.time()
    
    # Simple move history tracker (separate for each player)
    move_history = {0: [], 1: []}

    with GameLogger(out_dir=args.log_dir, game_id=args.game_id) as logger:
        for pid in (0, 1):
            if hasattr(agents[pid], "logger"):
                agents[pid].logger = logger
                agents[pid].player_id = pid

        done = False
        turn = 1
        max_turns = 100000
        while not done and turn < max_turns:
            player_id, observation = env.get_observation()
            print_board(observation)
            
            # Pass recent move history to agent
            agents[player_id].set_move_history(move_history[player_id][-10:])

            # Get agent action
            action = agents[player_id](observation)
            
            player_name = f"Player {player_id}"
            print(f"Turn {turn} | {player_name}[{agents[player_id].model_name}] -> {action}")

            # Execute move and get outcome
            done, outcome_info = env.step(action=action)
            
            # Process move details for logging
            move_details = process_move(
                action=action,
                board=env.env.board
            )
            
            # Record move in history
            move_history[player_id].append({
                "turn": turn,
                "move": action,
                "text": f"Turn {turn}: You played {action}"
            })

            # Log move
            logger.log_move(
                turn=turn,
                player=player_id,
                model_name=agents[player_id].model_name,
                move=action,
                src=move_details.src_pos,
                dst=move_details.dst_pos,
                piece_type=move_details.piece_type,
            )

            turn += 1
    
    # Finalize game
    rewards, game_info = env.close()
    game_duration = time.time() - game_start_time
    
    # Determine winner
    winner = None
    if rewards:
        if rewards.get(0, 0) > rewards.get(1, 0):
            winner = 0
        elif rewards.get(1, 0) > rewards.get(0, 0):
            winner = 1
    
    # Print summary
    print(f"\nGame finished. Duration: {int(game_duration // 60)}m {int(game_duration % 60)}s")
    print(f"Result: {rewards} | {game_info}")
    
    # LLM analyzes the game CSV and updates prompt
    analyze_and_update_prompt(
        csv_path=logger.path,
        prompts_dir="stratego/prompts",
        logs_dir=args.log_dir,
        model_name="mistral:7b",  # Analysis model
        models_used=[agents[0].model_name, agents[1].model_name],
        game_duration_seconds=game_duration,
        winner=winner,
        total_turns=turn - 1
    )


if __name__ == "__main__":
    cli()