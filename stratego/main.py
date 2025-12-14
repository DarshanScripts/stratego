import argparse
import os
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
from stratego.datasets import auto_push_after_game


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
def cli():
    DEFAULT_ENV = "Stratego-v0"
    DUEL_ENV = "Stratego-duel"
    CUSTOM_ENV = "Stratego-custom"
    tracker = MoveTrackerClass()
    p = argparse.ArgumentParser()
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
    p.add_argument("--max-turns", type=int, default=None, help="Maximum turns before stopping (for testing). E.g., --max-turns 10")

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
                # [CHANGE] Updated prompt range description
                board = input("Please enter your custom board size in range of 4~9: ").strip()
                # [CHANGE] Added '4' and '5' to valid options
                if board in ['4', '5', '6', '7', '8', '9']:
                    args.env_id = CUSTOM_ENV
                    args.size = int(board)
                    print(f"Selected: {CUSTOM_ENV} with size {args.size}x{args.size}")
                    break
                else:
                    print("Invalid choice.")
            else:
                print("Invalid choice.")

    # --- Setup Game ---
    agents = {
        0: build_agent(args.p0, args.prompt),
        1: build_agent(args.p1, args.prompt),
    }
    # Check if it is really normal Stratego version
    if (args.env_id == CUSTOM_ENV): 
        env = StrategoEnv(env_id=CUSTOM_ENV, size=args.size)
        game_type = "custom"
    elif (args.env_id == DUEL_ENV):
        env = StrategoEnv(env_id=DUEL_ENV)
        game_type = "duel"
        args.size = 6  # Duel mode uses 6x6 board
    else:
        env = StrategoEnv()
        game_type = "standard"
    env.reset(num_players=2)
    
    # Track game start time
    game_start_time = time.time()
    
    # Simple move history tracker (separate for each player)
    move_history = {0: [], 1: []}

    with GameLogger(out_dir=args.log_dir, game_id=args.game_id, prompt_name=args.prompt, game_type=game_type, board_size=args.size) as logger:
        for pid in (0, 1):
            if hasattr(agents[pid], "logger"):
                agents[pid].logger = logger
                agents[pid].player_id = pid

        done = False
        turn = 0
        print("\n--- Stratego LLM Match Started ---")
        print(f"Player 1 Agent: {agents[0].model_name}")
        print(f"Player 2 Agent: {agents[1].model_name}")
        if args.max_turns:
            print(f"⏱️  Max turns limit: {args.max_turns} (testing mode)")
        print()
        while not done:
            # Check max turns limit
            if args.max_turns and turn >= args.max_turns:
                print(f"\n⏱️  Reached max turns limit ({args.max_turns}). Stopping game early.")
                break
            
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
            
            # --- [CHANGE] INJECT AGGRESSION WARNING ---
            # If the game drags on (e.g. > 20 turns), force them to wake up
            if turn > 20:
                observation += "\n\n[SYSTEM MESSAGE]: The game is stalling. You MUST ATTACK or ADVANCE immediately. Passive play is forbidden."
            
            if turn > 50:
                 observation += "\n[CRITICAL]: STOP MOVING BACK AND FORTH. Pick a piece and move it FORWARD now."
            # ------------------------------------------

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

            # Extract move details for logging
            move_pattern = r'\[([A-J]\d+)\s+([A-J]\d+)\]'
            match = re.search(move_pattern, action)
            # src_pos = match.group(1) if match else ""
            # dst_pos = match.group(2) if match else ""
            
            # # Get piece type from board (simplified extraction)
            # piece_type = ""
            # if src_pos and hasattr(env, 'game_state') and hasattr(env.game_state, 'board'):
            #     try:
            #         # Parse position like "D4" -> row=3, col=3
            #         col = ord(src_pos[0]) - ord('A')
            #         row = int(src_pos[1:]) - 1
            #         piece = env.game_state.board[row][col]
            #         if piece and hasattr(piece, 'rank_name'):
            #             piece_type = piece.rank_name
            #     except:
            #         piece_type = "Unknown"
            
            # # Check if this is a repeated move (last 3 moves)
            # was_repeated = False
            # recent_moves = [m["move"] for m in move_history[player_id][-3:]]
            # if action in recent_moves:
            #     was_repeated = True
            
            # Record this move in history
            move_history[player_id].append({
                "turn": turn,
                "move": action,
                "text": f"Turn {turn}: You played {action}"
            })

            # Process move details for logging BEFORE making the environment step
            move_details = process_move(
                action=action,
                board=env.env.board,
                observation=observation,
                player_id=player_id
            )

            # Execute the action exactly once in the environment
            done, info = env.step(action=action)
            
            # Determine battle outcome by checking if target piece was there
            battle_outcome = ""
            if move_details.target_piece:
                # There was a piece at destination, so battle occurred
                # Check what's at destination now to determine outcome
                dst_row = ord(move_details.dst_pos[0]) - ord('A')
                dst_col = int(move_details.dst_pos[1:])
                cell_after = env.env.board[dst_row][dst_col]
                
                if cell_after is None:
                    # Both pieces removed = draw
                    battle_outcome = "draw"
                elif isinstance(cell_after, dict):
                    if cell_after.get('player') == player_id:
                        battle_outcome = "won"
                    else:
                        battle_outcome = "lost"
            
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
                                board_state=move_details.board_state,
                                available_moves=move_details.available_moves,
                                move_direction=move_details.move_direction,
                                target_piece=move_details.target_piece,
                                battle_outcome=battle_outcome,
                            )
            turn += 1


        # --- Game Over & Winner Announcement ---
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
        game_result = ""

        if p0_score > p1_score:
            winner = 0
            game_result = "player0"
            print(f"\n🏆 * * * PLAYER 0 WINS! * * * 🏆")
            print(f"Agent: {agents[0].model_name}")
        elif p1_score > p0_score:
            winner = 1
            game_result = "player1"
            print(f"\n🏆 * * * PLAYER 1 WINS! * * * 🏆")
            print(f"Agent: {agents[1].model_name}")
        else:
            game_result = "draw"
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
            
        # Finalize the game log with winner info in every row
        logger.finalize_game(winner=winner, game_result=game_result)
    
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
    
    # Auto-push game data to Hugging Face Hub
    print("\nSyncing game data to Hugging Face...")
    auto_push_after_game(
        logs_dir=os.path.join(args.log_dir, "games"),
        repo_id="STRATEGO-LLM-TRAINING/stratego",
    )
