# Import the 'argparse' library to manage command-line arguments
import argparse

# From the 'stratego_env_1' file, import the 'StrategoEnv' class
from stratego.env.stratego_env_2 import StrategoEnv 

# From your project, import the 'OllamaAgent' class
from stratego.models.ollama_model import OllamaAgent
# From your project, import the function that loads AI prompts
from stratego.prompts import get_prompt_pack
# From your project, import a helper function to clean up board text
from stratego.utils.parsing import extract_board_block_lines

# --- FUNCTION DEFINITIONS ---

# Define a function to create an AI agent object
def build_agent(spec: str,  prompt_name: str):
    # 'spec' is a string like "ollama:gemma3:1b". Split it at the first ':'
    kind, name = spec.split(":", 1)
    # Check if the 'kind' (the part before the ':') is "ollama"
    if kind == "ollama":
        # If yes, create and return a new OllamaAgent object
        return OllamaAgent(model_name=name, temperature=0.2, num_predict=32,
                           prompt_pack=get_prompt_pack(prompt_name))
    # If the 'kind' is not "ollama", stop the script with an error
    raise ValueError(f"Unknown agent spec: {spec}")

# Define a helper function to print the board neatly
def print_board(observation: str):
    # Use the parsing function to get only the board lines from the full text
    block = extract_board_block_lines(observation)
    # Check if 'block' is not empty (i.e., the function found a board)
    if block:
        # Join the list of lines ('block') into a single string separated by newlines
        print("\n".join(block))

# Define the main function that runs the "command-line interface" (cli)
def cli():
    # Create a new ArgumentParser object
    p = argparse.ArgumentParser()
    # Tell the parser to accept an argument named "--p0"
    p.add_argument("--p0", default="ollama:tinyllama", help="Agent spec for player 0")
    # Tell the parser to accept an argument named "--p1"
    p.add_argument("--p1", default="ollama:tinyllama", help="Agent spec for player 1")
    # Tell the parser to accept an argument named "--prompt"
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    # (The '--env_id' argument was removed so the user is prompted instead)
    
    # Read all the arguments provided by the user in the terminal
    args = p.parse_args()

    # --- NEW CODE: Ask the user which game to play ---
    # Print a header
    print("==============================================")
    # Print a welcome message
    print(" Welcome to Stratego")
    # Print another header
    print("==============================================")
    # Ask the user a question
    print("Which version would you like to play?")
    # Show option 1
    print("  1: Original Stratego (Stratego-v0)")
    # Show option 2
    print("  2: Stratego Duel (Stratego-duel)")
    
    # Wait for the user to type something and press Enter
    choice = input("Enter 1 or 2: ")

    # Check if the user's input string is exactly "1"
    if choice == "1":
        # If yes, create a string variable 'game_id'
        game_id = "Stratego-v0"
    # Otherwise, check if the user's input string is "2"
    elif choice == "2":
        # If yes, set 'game_id' to "Stratego-duel"
        game_id = "Stratego-duel"
    # If the user typed anything else
    else:
        # Print a message saying we are using the default
        print("Invalid choice, defaulting to Stratego-v0.")
        # Set 'game_id' to the default
        game_id = "Stratego-v0"
    # --- END OF NEW CODE ---

    # Create a 'dict' (dictionary) variable to hold the two AI agents
    agents = {
        # The key '0' maps to the agent for Player 0
        0: build_agent(args.p0, args.prompt),
        # The key '1' maps to the agent for Player 1
        1: build_agent(args.p1, args.prompt),
    }

    # Print a status message using the 'game_id' from the user's choice
    print(f"\nLoading game: {game_id}")
    # Create an instance of our 'StrategoEnv' class
    # 'env' is now an object variable
    env = StrategoEnv(env_id=game_id)
    # Call the 'reset' method on our 'env' object to start the game
    env.reset(num_players=2)

    # --- GAME LOOP ---
    # Create a boolean variable 'done' and set it to False
    done = False
    # Start a 'while' loop that will run as long as 'done' is False
    while not done:
        # Call the 'get_observation' method, which returns two values
        player_id, observation = env.get_observation()
        # Pass the observation text to our 'print_board' function
        print_board(observation)

        # Get the correct agent (0 or 1) from the 'agents' dictionary
        # Then, call the agent object as a function, passing it the observation
        # 'action' is a string variable, e.g., "[A1 B1]"
        action = agents[player_id](observation)
        # Print the player ID, model name, and the action it chose
        print(f"Player {player_id + 1} ({agents[player_id].model_name}) -> {action}")

        # Call the 'step' method on our 'env' object with the AI's action
        # 'done' will be updated to True if the game is over
        done, _ = env.step(action=action)

    # --- END OF GAME ---
    # The 'while' loop has finished
    # Call the 'close' method to get the final game results
    rewards, game_info = env.close()
    # Print the final results
    print("Game finished.", rewards, game_info)

# This is a standard Python entry point
# It checks if this file was run directly (not imported)
if __name__ == "__main__":
    # If run directly, call the 'cli' function to start the game
    cli()