"""
Main entry point for Stratego AI Battle Arena
This script runs AI vs AI games using vLLM models from HuggingFace.
Based on main_1.py structure with full vLLM support.
"""

# Import argparse library to handle command-line arguments
# Example: python main.py --p0 MODEL1 --p1 MODEL2
import argparse

# Import Dict type hint for dictionaries with specific key/value types
from typing import Dict

# Import the Stratego game environment from our project
# StrategoEnv class wraps TextArena's Stratego games
from stratego.env.stratego_env_2 import StrategoEnv

# Import our vLLM agent class (the only agent type we use now)
from stratego.models.vllm_model import VLLMAgent

# Import function to load prompt configurations
from stratego.prompts import get_prompt_pack

# Import utility function to extract and display board from observation text
from stratego.utils.parsing import extract_board_block_lines


def build_agent(spec: str, prompt_name: str):
    """
    Build an AI agent from a specification string.
    
    This function creates a VLLMAgent with the specified HuggingFace model.
    
    Args:
        spec (str): Agent specification in format "MODEL_ID" or "MODEL_ID:GPU_COUNT"
                   Examples:
                   - "google/gemma-2-2b-it" (use 1 GPU)
                   - "meta-llama/Llama-3.2-70B:4" (use 4 GPUs)
        prompt_name (str): Name of prompt preset ("base", "concise", "adaptive")
    
    Returns:
        VLLMAgent: Configured agent instance ready to play
    
    Raises:
        ValueError: If spec format is invalid
    """
    # Split spec string by colon to separate model name and GPU count
    # maxsplit=1 means only split on first colon (for model names with colons)
    parts = spec.split(":", 1)
    
    # Extract model name (everything before first colon, or entire string)
    model_name = parts[0]
    
    # Extract GPU count if specified, default to 1
    # If parts has 2 elements: ["MODEL_ID", "GPU_COUNT"]
    # If parts has 1 element: ["MODEL_ID"]
    gpus = int(parts[1]) if len(parts) > 1 else 1
    
    # Create and return VLLMAgent instance with configuration
    return VLLMAgent(
        model_name=model_name,              # Which HuggingFace model to use
        temperature=0.2,                    # Low temperature for more deterministic play
        max_tokens=64,                      # Limit response length
        tensor_parallel_size=gpus,          # How many GPUs to use
        prompt_pack=get_prompt_pack(prompt_name)  # Load prompt configuration
    )


def print_board(observation: str):
    """
    Extract and print the game board from observation text.
    
    The observation contains lots of text. This function extracts just the
    board visualization and prints it nicely.
    
    Args:
        observation (str): Full observation text from environment
    
    Returns:
        None (prints to console)
    """
    # Use parsing utility to extract board lines from observation
    # Returns list of strings, each representing one row of the board
    block = extract_board_block_lines(observation)
    
    # Check if board was found (block is not empty/None)
    if block:
        # Join list of lines with newlines and print
        # "\n".join() combines ["line1", "line2"] into "line1\nline2"
        print("\n".join(block))


def select_game() -> str:
    """
    Interactive prompt to let user choose game variant.
    
    This function displays a menu and waits for user input to select
    which version of Stratego to play.
    
    Returns:
        str: Game ID string ("Stratego-v0" or "Stratego-duel")
    """
    # Print header with decorative border
    print("\n" + "=" * 50)
    print(" Welcome to Stratego AI Battle Arena")
    print("=" * 50)
    
    # Display menu options
    print("\nWhich version would you like to play?")
    print("  1: Original Stratego (Stratego-v0)")
    print("     - Full 40x40 board")
    print("     - Complete piece set")
    print("  2: Stratego Duel (Stratego-duel)")
    print("     - Smaller 10-piece variant")
    print("     - Faster games")
    
    # Wait for user input and remove whitespace
    # input() pauses program until user types and presses Enter
    choice = input("\nEnter 1 or 2: ").strip()
    
    # Check user's choice and return appropriate game ID
    if choice == "1":
        return "Stratego-v0"
    elif choice == "2":
        return "Stratego-duel"
    else:
        # Invalid input - notify and use default
        print("Invalid choice, defaulting to Stratego-v0.")
        return "Stratego-v0"


def run_game(
    agent0_spec: str,      # String: model spec for player 0
    agent1_spec: str,      # String: model spec for player 1
    game_id: str,          # String: which game variant to play
    prompt_name: str,      # String: which prompt preset to use
    verbose: bool = True   # Boolean: whether to print detailed output
):
    """
    Run a single game between two AI agents.
    
    This is the main game loop that:
    1. Creates two agents
    2. Initializes the game environment
    3. Runs turns until game ends
    4. Returns final results
    
    Args:
        agent0_spec (str): Model specification for player 0
        agent1_spec (str): Model specification for player 1
        game_id (str): Game variant ID
        prompt_name (str): Prompt preset name
        verbose (bool): If True, print game progress. If False, minimal output.
    
    Returns:
        tuple: (rewards_dict, game_info_dict)
               rewards_dict maps player_id to final score
               game_info_dict contains metadata about the game
    """
    # Print status if verbose mode enabled
    if verbose:
        print(f"\n🤖 Building agents...")
        print(f"   Player 0: {agent0_spec}")
        print(f"   Player 1: {agent1_spec}")
    
    # Create dictionary mapping player IDs to agent objects
    # Key 0 maps to player 0's agent, key 1 maps to player 1's agent
    # Type hint: Dict[int, any] means keys are integers, values can be anything
    # 1. Create Agent 0 (This agent will initialize the vLLM engine)
    agent0 = build_agent(agent0_spec, prompt_name)
 
    # 2. Get the initialized vLLM engine instance from Agent 0.
    shared_llm_engine = agent0.llm 
 
    # 3. Create Agent 1 (This agent still runs build_agent, which creates an unwanted engine)
    agent1 = build_agent(agent1_spec, prompt_name)
 
    # 4. CRITICAL FIX: Overwrite Agent 1's unwanted LLM instance with the shared one from Agent 0.
    agent1.llm = shared_llm_engine
 
    # Create dictionary mapping player IDs to agent objects
    agents: Dict[int, any] = {
        0: agent0,
        1: agent1,
    }
    
    
    # Print loading status
    if verbose:
        print(f"\n🎮 Loading game: {game_id}")
    
    # Create game environment instance
    # StrategoEnv wraps TextArena's environment
    env = StrategoEnv(env_id=game_id)
    
    # Reset environment to start new game
    # num_players=2 specifies this is a 2-player game
    env.reset(num_players=2)
    
    # Initialize turn counter (tracks how many moves have been made)
    turn = 0
    
    # Initialize game state flag
    # done=False means game is ongoing, done=True means game ended
    done = False
    
    # Print game start banner
    if verbose:
        print(f"\n{'='*50}")
        print("🎲 GAME START")
        print(f"{'='*50}\n")
    
    # Main game loop - continues until done becomes True
    while not done:
        # Increment turn counter
        turn += 1
        
        # Get current observation from environment
        # Returns tuple: (player_id, observation_text)
        # player_id is 0 or 1 (whose turn it is)
        # observation_text describes current game state
        player_id, observation = env.get_observation()
        
        # Print turn information
        if verbose:
            # Get current player's model name from agents dictionary
            model_name = agents[player_id].model_name
            print(f"\n--- Turn {turn} | Player {player_id + 1} ({model_name}) ---")
            
            # Display the board
            print_board(observation)
        
        # Get action from current player's agent
        # Call agent like a function: agent(observation)
        # Returns move string like "[A0 B0]"
        action = agents[player_id](observation)
        
        # Print the action
        if verbose:
            print(f"➤ Action: {action}")
        
        # Execute action in environment
        # env.step() processes the move and updates game state
        # Returns tuple: (done, info)
        # done is True if game ended, False if game continues
        # We ignore info with _ since we don't need it in the loop
        done, _ = env.step(action=action)
    
    # Game loop ended - get final results
    # env.close() returns final rewards and game information
    rewards, game_info = env.close()
    
    # Print game over information
    if verbose:
        print(f"\n{'='*50}")
        print("🏁 GAME OVER")
        print(f"{'='*50}")
        print(f"Rewards: {rewards}")
        print(f"Info: {game_info}")
    
    # Clean up agents to free GPU memory
    for agent in agents.values():
        # Check if agent has cleanup method
        if hasattr(agent, 'cleanup'):
            # Call cleanup to free VRAM
            agent.cleanup()
    
    # Return game results
    return rewards, game_info


def cli():
    """
    Command-line interface for the game.
    
    This function:
    1. Parses command-line arguments
    2. Selects game variant
    3. Runs the game
    4. Displays winner
    """
    # Create argument parser object
    # ArgumentParser handles --flag and --option VALUE syntax
    parser = argparse.ArgumentParser(
        description="Stratego AI Battle Arena - vLLM HuggingFace Models",
        formatter_class=argparse.RawDescriptionHelpFormatter,  # Preserve formatting in epilog
        epilog="""
Examples:
  # Basic 2B vs 2B
  python -m stratego.main --p0 google/gemma-2-2b-it --p1 google/gemma-2-2b-it
  
  # 7B vs 3B models
  python -m stratego.main --p0 mistralai/Mistral-7B-Instruct-v0.3 --p1 meta-llama/Llama-3.2-3B-Instruct
  
  # Large model with 4 GPUs
  python -m stratego.main --p0 meta-llama/Llama-3.2-70B:4 --p1 Qwen/Qwen2.5-7B-Instruct
  
  # Specify game variant
  python -m stratego.main --game Stratego-duel --p0 google/gemma-2-2b-it --p1 mistralai/Mistral-7B-Instruct-v0.3
        """
    )
    
    # Add argument definitions
    # Each add_argument() defines a command-line flag
    parser.add_argument(
        "--p0",
        default="google/gemma-2-2b-it",  # Default model for player 0
        help="Player 0 model (HuggingFace ID or ID:GPU_COUNT)"
    )
    parser.add_argument(
        "--p1",
        default="google/gemma-2-2b-it",  # Default model for player 1
        help="Player 1 model (HuggingFace ID or ID:GPU_COUNT)"
    )
    parser.add_argument(
        "--game",
        default=None,  # None means ask user interactively
        help="Game variant: Stratego-v0 or Stratego-duel (interactive if not specified)"
    )
    parser.add_argument(
        "--prompt",
        default="base",
        help="Prompt preset: base, concise, or adaptive"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",  # Flag without value - presence means True
        help="Minimal output (no board display)"
    )
    
    # Parse command-line arguments
    # Returns Namespace object with attributes matching argument names
    args = parser.parse_args()
    
    # Select game: use command-line value if provided, otherwise ask user
    # Ternary operator: value_if_true if condition else value_if_false
    game_id = args.game if args.game else select_game()
    
    # Run game with error handling
    try:
        # Call run_game() with parsed arguments
        # verbose is opposite of quiet (not quiet = verbose)
        rewards, info = run_game(
            agent0_spec=args.p0,
            agent1_spec=args.p1,
            game_id=game_id,
            prompt_name=args.prompt,
            verbose=not args.quiet
        )
        
        # Determine and announce winner
        # Compare rewards to see who won
        if rewards[0] > rewards[1]:
            print("\n🏆 Player 0 WINS!")
        elif rewards[1] > rewards[0]:
            print("\n🏆 Player 1 WINS!")
        else:
            print("\n🤝 DRAW!")
    
    # Handle keyboard interrupt (Ctrl+C)
    except KeyboardInterrupt:
        print("\n\n⚠️  Game interrupted by user")
    
    # Handle any other errors
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise  # Re-raise exception to show full traceback


# Python entry point
# This code only runs when file is executed directly (not imported)
if __name__ == "__main__":
    # Call cli() to start the program
    cli()