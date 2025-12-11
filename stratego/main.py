import argparse
<<<<<<< HEAD
import re
import time
import random
# from stratego.prompt_optimizer import improve_prompt
from stratego.env.stratego_env import StrategoEnv
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines, extract_legal_moves, extract_forbidden
from stratego.utils.game_move_tracker import GameMoveTracker as MoveTrackerClass
from stratego.utils.move_processor import process_move
from stratego.game_logger import GameLogger
from stratego.game_analyzer import analyze_and_update_prompt


#Revised to set temperature(13 Nov 2025)
def build_agent(spec: str, prompt_name: str):
    """ 
    Creates and configures an AI agent based on the input string.
    Example spec: 'ollama:phi3:3.8b'
    """
    kind, name = spec.split(":", 1)  # Split string to get model type and name
    
    if kind == "ollama":
        from stratego.models.ollama_model import OllamaAgent
        # Define the temperature value explicitly
        AGENT_TEMPERATURE = 0.2
        
        # Create the Ollama agent
        agent = OllamaAgent(
            model_name=name, 
            temperature=AGENT_TEMPERATURE, 
            num_predict=128,  # Allow enough tokens for a complete move response
            prompt_pack=get_prompt_pack(prompt_name) # Load strategy prompt
        )
        
        # Store temperature for logging
        agent.temperature = AGENT_TEMPERATURE
        
        return agent
    if kind == "hf":
        from stratego.models.hf_model import HFLocalAgent
        return HFLocalAgent(model_id=name, prompt_pack=prompt_name)
    raise ValueError(f"Unknown agent spec: {spec}")

def print_board(observation: str, size: int = 10):
    block = extract_board_block_lines(observation, size)
    if block:
        print("\n".join(block))

# --- Main Command Line Interface (CLI) ---
=======
from stratego.env.custom_env import CustomStrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack

from stratego.strategies.aggressive_strategy import AggressiveStrategy
from stratego.strategies.defensive_strategy import DefensiveStrategy
from stratego.strategies.random_move import RandomStrategy


# ---------------------- Agent builder ----------------------
def build_agent(spec: str, prompt_name: str, strategy_name: str):
    kind, name = spec.split(":", 1)

    strategy_map = {
        "aggressive": AggressiveStrategy(),
        "defensive": DefensiveStrategy(),
        "random": RandomStrategy(),
    }
    strategy = strategy_map.get(strategy_name, RandomStrategy())

    if kind == "ollama":
        return OllamaAgent(
            model_name=name,
            temperature=0.2,
            num_predict=32,
            prompt_pack=get_prompt_pack(prompt_name),
            strategy=strategy,
        )
    raise ValueError(f"Unknown agent spec: {spec}")


# ---------------------- Board printing ----------------------
def print_board(observation: str):
    """
    Formatează observația într-o afișare de tip tabel.
    Caută secțiunea 'Board:' și o afișează cu litere + numere.
    """
    lines = observation.splitlines()
    board_lines = []
    start = False
    for line in lines:
        if line.strip().lower().startswith("board"):
            start = True
            continue
        if start:
            if not line.strip():
                break
            board_lines.append(line.strip())

    if not board_lines:
        print(observation)
        return

    n = len(board_lines)
    print("\n    " + "   ".join(str(i) for i in range(len(board_lines[0].split()))))
    for idx, row in enumerate(board_lines):
        print(chr(65 + idx) + "   " + "   ".join(row.split()))
    print()


# ---------------------- Main CLI ----------------------
>>>>>>> 2010f743cd849c0c74ee1f8e3578ba864676ced5
def cli():
    DEFAULT_ENV = "Stratego-v0"
    DUEL_ENV = "Stratego-duel"
    CUSTOM_ENV = "Stratego-custom"
    tracker = MoveTrackerClass()
    p = argparse.ArgumentParser()
<<<<<<< HEAD
    p.add_argument("--p0", default="ollama:phi3:3.8b")
    p.add_argument("--p0", default="ollama:deepseek-r1:32b")
    p.add_argument("--p1", default="ollama:gemma3:1b")
    # UPDATED HELP TEXT to explain how this parameter relates to VRAM utilization
    # For large models (120B, 70B), you MUST set this value based on available VRAM(13 Nov 2025)
    # UPDATED GPU arguments for VRAM control (now defaults to CPU-only)
    p.add_argument("--p0-num-gpu", type=int, default=0,
                    help="Number of GPU layers to offload for Player 0. Default is 0 (CPU-only mode). Use a positive number (e.g., 50) to offload layers to GPU/VRAM, or 999 for maximum GPU use.")
    p.add_argument("--p1-num-gpu", type=int, default=0,
                    help="Number of GPU layers to offload for Player 1. Default is 0 (CPU-only mode). Use a positive number (e.g., 40) to offload layers to GPU/VRAM, or 999 for maximum GPU use.")    
    #(13 Nov 2025) NOTE: Default env_id is used as a flag to trigger the interactive menu
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--env_id", default=DEFAULT_ENV, help="TextArena environment id")
    p.add_argument("--log-dir", default="logs", help="Directory for per-game CSV logs")
    p.add_argument("--game-id", default=None, help="Optional custom game id in CSV filename")
    p.add_argument("--size", type=int, default=10, help="Board size NxN")

    args = p.parse_args()

    #(13 Nov 2025) --- INTERACTIVE ENVIRONMENT SELECTION ---
    if args.env_id == DEFAULT_ENV:
        print("\n--- Stratego Version Selection ---")
        print(f"1. Standard Game ({DEFAULT_ENV})")
        print(f"2. Duel Mode ({DUEL_ENV})")
        print(f"3. Custom Mode ({CUSTOM_ENV})")
        
        while True:
            choice = input("Enter your choice (1, 2, or 3): ").strip()
            if not choice or choice == '1':
                print(f"Selected: {DEFAULT_ENV}")
                break
            elif choice == '2':
                args.env_id = DUEL_ENV
                args.size = 6
                print(f"Selected: {DUEL_ENV}")
                break
            elif choice == '3':
                board = input("Please enter your custom board size in range of 6~9: ").strip()
                if board in ['6', '7', '8', '9']:
                    args.env_id = CUSTOM_ENV
                    args.size = int(board)
                    print(f"Selected: {CUSTOM_ENV} with size {args.size}x{args.size}")
                    break
                else:
                    print("Invalid choice.")
            else:
                print("Invalid choice.")

    # --- Setup Game ---
=======
    p.add_argument("--p0", default="ollama:gemma3:270m")
    p.add_argument("--p1", default="ollama:qwen2.5:0.5b")
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--env_id", default="Stratego-v0", help="Environment id")
    p.add_argument("--s0", default="aggressive", help="Strategy for player 0")
    p.add_argument("--s1", default="defensive", help="Strategy for player 1")
    p.add_argument("--size", type=int, default=10, help="Board size (NxN)")
    args = p.parse_args()

    # Creăm agenții
>>>>>>> 2010f743cd849c0c74ee1f8e3578ba864676ced5
    agents = {
        0: build_agent(args.p0, args.prompt, args.s0),
        1: build_agent(args.p1, args.prompt, args.s1),
    }
<<<<<<< HEAD
    # Check if it is really normal Stratego version
    if (args.env_id == CUSTOM_ENV): 
        env = StrategoEnv(env_id=CUSTOM_ENV, size=args.size)
    elif (args.env_id == DUEL_ENV):
        env = StrategoEnv(env_id=DUEL_ENV)
    else:
        env = StrategoEnv()
=======

    # Inițializăm mediul personalizat
    env = CustomStrategoEnv(env_id=args.env_id, board_size=args.size)
>>>>>>> 2010f743cd849c0c74ee1f8e3578ba864676ced5
    env.reset(num_players=2)
    
    # Track game start time
    game_start_time = time.time()
    
    # Simple move history tracker (separate for each player)
    move_history = {0: [], 1: []}

<<<<<<< HEAD
    with GameLogger(out_dir=args.log_dir, game_id=args.game_id) as logger:
        for pid in (0, 1):
            if hasattr(agents[pid], "logger"):
                agents[pid].logger = logger
                agents[pid].player_id = pid

        done = False
        turn = 0
        print("\n--- Stratego LLM Match Started ---")
        print(f"Player 1 Agent: {agents[0].model_name}")
        print(f"Player 2 Agent: {agents[1].model_name}\n")
        while not done:
            player_id, observation = env.get_observation()
            current_agent = agents[player_id]
            player_display = f"Player {player_id+1}"
            model_name = current_agent.model_name
            
            # --- NEW LOGGING FOR TURN, PLAYER, AND MODEL ---
            print(f"\n>>>> TURN {turn}: {player_display} ({model_name}) is moving...")

            if (args.size == 10):
                print_board(observation)
            else:
                print_board(observation, args.size)
            # Pass recent move history to agent
            current_agent.set_move_history(move_history[player_id][-10:])
            history_str = tracker.to_prompt_string(player_id)
            observation = observation + history_str
            # print(tracker.to_prompt_string(player_id))
            lines = history_str.strip().splitlines()
            if len(lines) <= 1:
                print(history_str)
            else:
                header = lines[0:1]
                body = lines[1:]
                tail = body[-5:]  # Show only last 5 moves
                print("\n".join(header + tail))
            
            # The agent (LLM) generates the action, retry a few times; fallback to available moves
            action = ""
            max_agent_attempts = 3
            for attempt in range(max_agent_attempts):
                action = current_agent(observation)
                if action:
                    break
                print(f"[TURN {turn}] {model_name} failed to produce a move (attempt {attempt+1}/{max_agent_attempts}). Retrying...")

            if not action:
                legal = extract_legal_moves(observation)
                forbidden = set(extract_forbidden(observation))
                legal_filtered = [m for m in legal if m not in forbidden] or legal
                if legal_filtered:
                    action = random.choice(legal_filtered)
                    print(f"[TURN {turn}] Fallback to random available move: {action}")
                else:
                    print(f"[TURN {turn}] No legal moves available for fallback; ending game loop.")
                    break
            # --- NEW LOGGING FOR STRATEGY/MODEL DECISION ---
            print(f"  > AGENT DECISION: {model_name} -> {action}")
            print(f"  > Strategy/Model: Ollama Agent (T={current_agent.temperature}, Prompt='{args.prompt}')")
            
            done, info = env.step(action=action)
            
            
            # Process move details for logging
            move_details = process_move(
                action=action,
                board=env.env.board
            )
            
            # Extract outcome from environment observation
            outcome = "move"
            # captured = ""
            obs_text = ""
            # if isinstance(info, (list, tuple)) and len(info) > 1:
            #     obs_text = str(info[1])
            # else:
            #     obs_text = str(info)
            if isinstance(info, (list, tuple)):
                if 0 <= player_id < len(info):
                    obs_text = str(info[player_id])
                else:
                    obs_text = " ".join(str(x) for x in info)
            else:
                obs_text = str(info)

            low = obs_text.lower()
            if "invalid" in low or "illegal" in low:
                outcome = "invalid"
            elif "captured" in low or "won the battle" in low:
                outcome = "won_battle"
            elif "lost the battle" in low or "defeated" in low:
                outcome = "lost_battle"
            elif "draw" in low or "tie" in low:
                outcome = "draw"
                    
            event = info.get("event") if isinstance(info, dict) else None
            extra = info.get("detail") if isinstance(info, dict) else None
            
            if outcome != "invalid":
                # Record this move in history
                move_history[player_id].append({
                    "turn": turn,
                    "move": action,
                    "text": f"Turn {turn}: You played {action}"
                })

                tracker.record(
                    player=player_id,
                    move=action,
                    event=event,
                    extra=extra
                )
            else:
                move_history[player_id].append({
                    "turn": turn,
                    "move": action,
                    "text": f"Turn {turn}: INVALID move {action}"
                })
                tracker.record(
                    player=player_id,
                    move=action,
                    event="invalid_move",
                    extra=extra
                )
                print(f"[HISTORY] Skipping invalid move from history: {action}")

            logger.log_move(turn=turn,
                                player=player_id,
                                model_name=getattr(current_agent, "model_name", "unknown"),
                                move=action,
                                src=move_details.src_pos,
                                dst=move_details.dst_pos,
                                piece_type=move_details.piece_type,
                                outcome=outcome,
                                # captured=captured,
                                # was_repeated=was_repeated
                            )
            turn += 1


    # --- Game Over & Winner Announcement ---
=======
    done = False
    step_count = 0
    max_steps = 50

    print(f"\n=== Starting Stratego on a {args.size}x{args.size} board ===\n")

    while not done and step_count < max_steps:
        player_id, observation = env.get_observation()

        print_board(observation)

        # Agentul alege o mutare
        action = agents[player_id](observation)
        if not action:
            print(f"{agents[player_id].model_name} -> (no move)")
        else:
            print(f"{agents[player_id].model_name} -> [{action}]")

        # Aplicăm mutarea
        done, _ = env.step(action=action)

        # Afișăm tabla după mutare
        _, new_obs = env.get_observation()
        print_board(new_obs)

        step_count += 1

    print(f"Game stopped after {step_count} steps.")
>>>>>>> 2010f743cd849c0c74ee1f8e3578ba864676ced5
    rewards, game_info = env.close()
    print("\n" + "="*50)
    print("--- GAME OVER ---")
    game_duration = time.time() - game_start_time
    # Print summary
    print(f"\nGame finished. Duration: {int(game_duration // 60)}m {int(game_duration % 60)}s")
    print(f"Result: {rewards} | {game_info}")
    
    # Logic to declare the specific winner based on rewards
    # Rewards are usually {0: 1, 1: -1} (P0 Wins) or {0: -1, 1: 1} (P1 Wins)
    p0_score = rewards.get(0, 0)
    p1_score = rewards.get(1, 0)
    winner = None

    if p0_score > p1_score:
        winner = 0
        print(f"\n🏆 * * * PLAYER 0 WINS! * * * 🏆")
        print(f"Agent: {agents[0].model_name}")
    elif p1_score > p0_score:
        winner = 1
        print(f"\n🏆 * * * PLAYER 1 WINS! * * * 🏆")
        print(f"Agent: {agents[1].model_name}")
    else:
        print(f"\n🤝 * * * IT'S A DRAW! * * * 🤝")

    print("\nDetails:")
    print(f"Final Rewards: {rewards}")
    print(f"Game Info: {game_info}")
    
    try:
        invalid_players = [
            pid for pid, info_dict in (game_info or {}).items()
            if isinstance(info_dict, dict) and info_dict.get("invalid_move")
        ]
        if invalid_players:
            import csv
            csv_path = logger.path
            rows = []
            fieldnames = None

            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for r in reader:
                    rows.append(r)

            if rows and fieldnames and "outcome" in fieldnames:
                rows[-1]["outcome"] = "invalid"
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

                print("\n[LOG PATCH] Last move outcome patched to 'invalid' "
                      f"(player {invalid_players[0]} made an invalid move).")
                
    except Exception as e:
        print(f"[LOG PATCH] Failed to patch CSV outcome: {e}")
        
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
    
    # num_games = len([f for f in os.listdir(args.log_dir) if f.endswith(".csv")])
    # if num_games % 1 == 0:
    #     print("Running prompt improvement based on recent games...")
    #     improve_prompt(args.log_dir, "stratego/prompts/current_prompt.txt", model_name="phi3:14b")



if __name__ == "__main__":
    cli()
