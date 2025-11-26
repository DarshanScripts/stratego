import argparse  # Library for handling command-line arguments
import sys      # Library for system-specific parameters and functions
from stratego.env.stratego_env_2 import StrategoEnv  # Import our custom Environment wrapper
from stratego.models.ollama_model import OllamaAgent # Import the AI Agent model
from stratego.prompts import get_prompt_pack         # Import prompt templates
from stratego.utils.parsing import extract_board_block_lines # Utility to extract board text

# --- Function to configure the AI Agent ---
def build_agent(spec: str, prompt_name: str):
    """ 
    Creates and configures an AI agent based on the input string.
    Example spec: 'ollama:phi3:3.8b'
    """
    kind, name = spec.split(":", 1)  # Split string to get model type and name
    
    if kind == "ollama":
        # AGENT_TEMPERATURE controls creativity (0.2 = focused/logical)
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
        
        return agent # Return initialized agent
        
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
    # Create argument parser
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:mistral:7b")
    p.add_argument("--p1", default="ollama:gemma:2b")
    p.add_argument("--p0-num-gpu", type=int, default=0)
    p.add_argument("--p1-num-gpu", type=int, default=0)
    p.add_argument("--prompt", default="base")
    p.add_argument("--env_id", default="Stratego-v0")
    args = p.parse_args() 

    DEFAULT_ENV = "Stratego-v0"
    CUSTOM_ENV = "Stratego-duel"

    # --- Interactive Menu ---
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
    
    # Initialize Environment (Calls wrapper in stratego_env_2.py)
    env = StrategoEnv(env_id=args.env_id)
    env.reset(num_players=2)

    done = False
    turn_count = 0

    print("\n--- Stratego LLM Match Started ---")
    print(f"Player 0: {agents[0].model_name}")
    print(f"Player 1: {agents[1].model_name}\n")

    # --- Main Game Loop ---
    while not done:
        turn_count += 1
        player_id, observation = env.get_observation()
        
        # --- Data Cleaning ---
        raw_item = observation
        if isinstance(raw_item, list):
            raw_item = raw_item[-1] if raw_item else ""

        # Unwrap Tuple to get Message String
        if isinstance(raw_item, tuple):
            if len(raw_item) >= 2:
                current_observation_str = str(raw_item[1]) 
            else:
                current_observation_str = str(raw_item[-1])
        else:
            current_observation_str = str(raw_item)

        current_agent = agents[player_id]
        model_name = current_agent.model_name
        
        print(f"\n>>>> TURN {turn_count}: Player {player_id} ({model_name}) is moving...")
        
        # Print Board
        print_board(current_observation_str)
        
        # --- AI Decision ---
        action = current_agent(current_observation_str)

        # Safety Check for empty output
        if not action or not str(action).strip():
            print("  > [WARNING] AI returned empty string. Sending [PASS].")
            action = "[PASS]" 

        # Logging
        temp_val = getattr(current_agent, 'temperature', 'N/A')
        print(f"  > AGENT OUTPUT: {repr(action)}")
        print(f"  > Strategy: Ollama (T={temp_val})")

        # Execute Move
        done, _ = env.step(action=action)

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

if __name__ == "__main__":
    cli()