from stratego.prompt_optimizer import improve_prompt
import os
import argparse
from stratego.env.stratego_env import StrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines
from stratego.game_logger import GameLogger

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
    
    # Simple move history tracker (separate for each player)
    move_history = {0: [], 1: []}

    with GameLogger(out_dir=args.log_dir, game_id=args.game_id) as logger:
        for pid in (0, 1):
            if hasattr(agents[pid], "logger"):
                agents[pid].logger = logger
                agents[pid].player_id = pid
            initial = getattr(agents[pid], "initial_prompt", None)
            if initial:
                logger.log_prompt(player=pid,
                                  model_name=getattr(agents[pid], "model_name", "unknown"),
                                  prompt=initial,
                                  role="initial")

        done = False
        turn = 1
        max_turns = 10
        while not done and turn < max_turns:
            player_id, observation = env.get_observation()
            print_board(observation)
            
            # Pass recent move history to agent
            agents[player_id].set_move_history(move_history[player_id][-10:])

            action = agents[player_id](observation)
            player_name = "Player 0" if player_id == 0 else "Player 1"
            print(f"Turn {turn} | {player_name}[{agents[player_id].model_name}] -> {action}")
            
            # Extract move details for logging
            import re
            move_pattern = r'\[([A-J]\d+)\s+([A-J]\d+)\]'
            match = re.search(move_pattern, action)
            src_pos = match.group(1) if match else ""
            dst_pos = match.group(2) if match else ""
            
            # Get piece type from board (simplified extraction)
            piece_type = ""
            if src_pos and hasattr(env, 'game_state') and hasattr(env.game_state, 'board'):
                try:
                    # Parse position like "D4" -> row=3, col=3
                    col = ord(src_pos[0]) - ord('A')
                    row = int(src_pos[1:]) - 1
                    piece = env.game_state.board[row][col]
                    if piece and hasattr(piece, 'rank_name'):
                        piece_type = piece.rank_name
                except:
                    piece_type = "Unknown"
            
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
            
            # Extract outcome from environment observation
            outcome = "move"
            captured = ""
            if outcome_info and len(outcome_info) > 1:
                obs_text = str(outcome_info[1]) if len(outcome_info) > 1 else ""
                if "won" in obs_text.lower() or "captured" in obs_text.lower():
                    outcome = "won_battle"
                    # Try to extract captured piece name
                    cap_match = re.search(r'captured.*?(\w+)', obs_text, re.IGNORECASE)
                    if cap_match:
                        captured = cap_match.group(1)
                elif "lost" in obs_text.lower() or "defeated" in obs_text.lower():
                    outcome = "lost_battle"
                elif "draw" in obs_text.lower() or "tie" in obs_text.lower():
                    outcome = "draw"
                elif "invalid" in obs_text.lower() or "illegal" in obs_text.lower():
                    outcome = "invalid"

            logger.log_move(turn=turn,
                                player=player_id,
                                model_name=getattr(agents[player_id], "model_name", "unknown"),
                                move=action,
                                src=src_pos,
                                dst=dst_pos,
                                piece_type=piece_type,
                                outcome=outcome,
                                captured=captured,
                                was_repeated=was_repeated)

            turn += 1
    rewards, game_info = env.close()
    print("Game finished.", rewards, game_info)
    
    num_games = len([f for f in os.listdir(args.log_dir) if f.endswith(".csv")])
    if num_games % 1 == 0:
        print("Running prompt improvement based on recent games...")
        from stratego.prompt_optimizer import improve_prompt
        improve_prompt(args.log_dir, "stratego/prompts/current_prompt.txt", model_name="phi3:14b")


if __name__ == "__main__":
    cli()