import argparse
import re
from stratego.prompt_optimizer import improve_prompt
import os
import sys
from stratego.env.stratego_env_2 import StrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines
from stratego.custom_env import CustomStrategoEnv as CustomEnv
from stratego.utils.game_move_tracker import GameMoveTracker as MoveTrackerClass
from stratego.game_logger import GameLogger

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

# --- Function to Print the Board ---
def print_board(observation):
    """ 
    Robust function to print the game board to the console.
    Handles data types (List/Tuple/String) safely.
    """
    # 1. Handle List input (History of observations)
    if isinstance(observation, list):
        # If list is not empty, take the last item (most recent state)
        observation = observation[-1] if observation else ""
    
    # 2. Handle Tuple input (SenderID, Message, Type)
    # We want index 1 (the message), not index -1 (the type)
    if isinstance(observation, tuple):
        if len(observation) >= 2:
            observation = str(observation[1]) 
        else:
            observation = str(observation[-1])
    
    # Ensure observation is a string
    observation = str(observation)

    # 3. Try standard extraction method (works for 10x10 standard board)
    block = extract_board_block_lines(observation)
    if block:
        print("\n" + "="*50)
        print("\n".join(block))
        return

    # 4. Fallback extraction (works for our 6x6 board with backticks ```)
    if "```" in observation:
        print("\n" + "="*50)
        try:
            parts = observation.split("```") # Split string by backticks
            if len(parts) > 1:
                # Extract middle part, remove whitespace, and fix escape characters (\n)
                print(parts[1].strip().encode().decode('unicode_escape')) 
            else:
                print(observation) # Print raw if split fails
        except:
            print(observation)
    else:
        # 5. Last resort: Print raw text, but filter out internal Enum strings
        if "ObservationType" not in observation:
            print("\n[DEBUG RAW BOARD DATA]:")
            print(observation)

# --- Main Command Line Interface (CLI) ---
def cli():
    tracker = MoveTrackerClass()
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:phi3:3.8b")
    p.add_argument("--p1", default="ollama:gemma3:1b")

    # UPDATED HELP TEXT to explain how this parameter relates to VRAM utilization
    # For large models (120B, 70B), you MUST set this value based on available VRAM(13 Nov 2025)
    # UPDATED GPU arguments for VRAM control (now defaults to CPU-only)
    p.add_argument("--p0-num-gpu", type=int, default=0,
                    help="Number of GPU layers to offload for Player 0. Default is 0 (CPU-only mode). Use a positive number (e.g., 50) to offload layers to GPU/VRAM, or 999 for maximum GPU use.")
    p.add_argument("--p1-num-gpu", type=int, default=0,
                    help="Number of GPU layers to offload for Player 1. Default is 0 (CPU-only mode). Use a positive number (e.g., 40) to offload layers to GPU/VRAM, or 999 for maximum GPU use.")
    
    #(13 Nov 2025) NOTE: Default env_id is used as a flag to trigger the interactive menu
    DEFAULT_ENV = "Stratego-v0"
    CUSTOM_ENV = "Stratego-duel"

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
        print(f"2. Duel Mode ({CUSTOM_ENV})")
        
        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if not choice or choice == '1':
                print(f"Selected: {DEFAULT_ENV}")
                break
            elif choice == '2':
                args.env_id = CUSTOM_ENV
                print(f"Selected: {CUSTOM_ENV}")
                break
            else:
                print("Invalid choice.")

    # --- Setup Game ---
    agents = {
        0: build_agent(args.p0, args.prompt),
        1: build_agent(args.p1, args.prompt),
    }
    # Check if it is really normal Stratego version
    if (args.env_id == "Stratego-v0" and args.size == 10):
        env = StrategoEnv()
    # Else, it is custom version
    elif (args.size != 10): 
        env = CustomEnv(size=args.size)
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
                
        for pid in (0, 1):
            initial = getattr(agents[pid], "initial_prompt", None)
            if initial:
                logger.log_prompt(
                    player=pid,
                    model_name=getattr(agents[pid], "model_name", "unknown"),
                    prompt=initial,
                    role="initial"
                )

    done = False
    turn = 0
    print("\n--- Stratego LLM Match Started ---")
    print(f"Player 1 Agent: {agents[0].model_name}")
    print(f"Player 2 Agent: {agents[1].model_name}\n")
    while not done:
        turn += 1
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
            observation = observation + tracker.to_prompt_string(player_id)
            print(tracker.to_prompt_string(player_id))
        
        # The agent (LLM) generates the action
        action = current_agent(observation)
        
        # --- NEW LOGGING FOR STRATEGY/MODEL DECISION ---
        print(f"  > AGENT DECISION: {model_name} -> {action}")
        print(f"  > Strategy/Model: Ollama Agent (T={current_agent.temperature}, Prompt='{args.prompt}')")

        # Extract move details for logging
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

        done, info = env.step(action=action)

        event = info.get("event") if isinstance(info, dict) else None
        extra = info.get("detail") if isinstance(info, dict) else None

        tracker.record(
            player=player_id,
            move=action,
            event=event,
            extra=extra
        )

        logger.log_move(turn=turn,
                            player=player_id,
                            model_name=getattr(current_agent, "model_name", "unknown"),
                            move=action,
                            src=src_pos,
                            dst=dst_pos,
                            piece_type=piece_type,
                            outcome=outcome,
                            captured=captured,
                            was_repeated=was_repeated)


    # --- Game Over & Winner Announcement ---
    rewards, game_info = env.close()
    print("\n" + "="*50)
    print("--- GAME OVER ---")
    
    # Logic to declare the specific winner based on rewards
    # Rewards are usually {0: 1, 1: -1} (P0 Wins) or {0: -1, 1: 1} (P1 Wins)
    p0_score = rewards.get(0, 0)
    p1_score = rewards.get(1, 0)

    if p0_score > p1_score:
        print(f"\n🏆 * * * PLAYER 0 WINS! * * * 🏆")
        print(f"Agent: {agents[0].model_name}")
    elif p1_score > p0_score:
        print(f"\n🏆 * * * PLAYER 1 WINS! * * * 🏆")
        print(f"Agent: {agents[1].model_name}")
    else:
        print(f"\n🤝 * * * IT'S A DRAW! * * * 🤝")

    print("\nDetails:")
    print(f"Final Rewards: {rewards}")
    print(f"Game Info: {game_info}")
    
    num_games = len([f for f in os.listdir(args.log_dir) if f.endswith(".csv")])
    if num_games % 1 == 0:
        print("Running prompt improvement based on recent games...")
        from stratego.prompt_optimizer import improve_prompt
        improve_prompt(args.log_dir, "stratego/prompts/current_prompt.txt", model_name="phi3:14b")


if __name__ == "__main__":
    cli()