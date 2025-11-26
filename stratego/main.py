from stratego.prompt_optimizer import improve_prompt_after_game
import os
import re
import time
import argparse
from stratego.env.stratego_env import StrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines
from stratego.game_logger import GameLogger

# Piece rank mapping for logging
PIECE_RANKS = {
    'Flag': 0, 'Spy': 1, 'Scout': 2, 'Miner': 3, 'Sergeant': 4,
    'Lieutenant': 5, 'Captain': 6, 'Major': 7, 'Colonel': 8,
    'General': 9, 'Marshal': 10, 'Bomb': 11
}

def build_agent(spec: str,  prompt_name: str):
    kind, name = spec.split(":", 1)
    if kind == "ollama":
        return OllamaAgent(model_name=name, temperature=0.2, num_predict=32,
                           prompt_pack=get_prompt_pack(prompt_name))
    raise ValueError(f"Unknown agent spec: {spec}")

# Later we can make printing board method as more in detail.
def print_board(observation: str):
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

            # Time the agent response
            move_start = time.time()
            action = agents[player_id](observation)
            response_time_ms = int((time.time() - move_start) * 1000)
            
            player_name = "Player 0" if player_id == 0 else "Player 1"
            print(f"Turn {turn} | {player_name}[{agents[player_id].model_name}] -> {action} ({response_time_ms}ms)")
            
            # Extract move details for logging
            move_pattern = r'\[([A-J]\d+)\s+([A-J]\d+)\]'
            match = re.search(move_pattern, action)
            src_pos = match.group(1) if match else ""
            dst_pos = match.group(2) if match else ""
            
            # Get piece type and rank from board
            piece_type = ""
            piece_rank = None
            if src_pos:
                try:
                    row = ord(src_pos[0]) - ord('A')
                    col = int(src_pos[1:])
                    board = env.env.board
                    piece = board[row][col]
                    if piece and isinstance(piece, dict) and 'rank' in piece:
                        piece_type = piece['rank']
                        piece_rank = PIECE_RANKS.get(piece_type)
                except Exception:
                    pass
            
            # Check if this is a repeated move (last 3 moves)
            was_repeated = False
            recent_moves = [m["move"] for m in move_history[player_id][-3:]]
            if action in recent_moves:
                was_repeated = True
            
            # Record this move in history
            move_history[player_id].append({
                "turn": turn,
                "move": action,
                "text": f"Turn {turn}: You played {action}"
            })

            done, outcome_info = env.step(action=action)
            
            # Simple outcome - just move or battle
            outcome = "move"
            if outcome_info and len(outcome_info) > 1:
                obs_text = str(outcome_info[1]).lower()
                if any(word in obs_text for word in ["won", "lost", "captured", "defeated", "draw", "tie"]):
                    outcome = "battle"

            logger.log_move(
                turn=turn,
                player=player_id,
                model_name=getattr(agents[player_id], "model_name", "unknown"),
                move=action,
                src=src_pos,
                dst=dst_pos,
                piece_type=piece_type,
                piece_rank=piece_rank,
                outcome=outcome,
                was_repeated=was_repeated,
                response_time_ms=response_time_ms
            )

            turn += 1
        
        # Get problem summary before closing logger (inside with block)
        problem_summary = logger.get_problem_summary(winner=None)
    
    rewards, game_info = env.close()
    
    # Calculate game duration
    game_duration = time.time() - game_start_time
    duration_min = int(game_duration // 60)
    duration_sec = int(game_duration % 60)
    
    print("Game finished.", rewards, game_info)
    print(f"Game duration: {duration_min}m {duration_sec}s")
    
    # Determine winner from rewards
    winner = None
    if rewards:
        if rewards.get(0, 0) > rewards.get(1, 0):
            winner = 0
        elif rewards.get(1, 0) > rewards.get(0, 0):
            winner = 1
    
    # Automatic prompt improvement based on this game's mistakes
    if problem_summary:
        problem_summary.winner = winner
        
        print(f"\n--- Game Analysis ---")
        print(f"Total turns: {problem_summary.total_turns}")
        print(f"Repeated moves: {len(problem_summary.repeated_moves)}")
        print(f"Back-and-forth patterns: {len(problem_summary.back_and_forth)}")
        print(f"Battles: {problem_summary.battles_won} won, {problem_summary.battles_lost} lost")
        
        # Get model names for logging
        model_names = [agents[0].model_name, agents[1].model_name]
        
        # Improve prompt based on specific mistakes
        improve_prompt_after_game(
            problem_summary, 
            prompts_dir="stratego/prompts",
            logs_dir=args.log_dir,
            models=model_names,
            game_duration_seconds=game_duration
        )


if __name__ == "__main__":
    cli()