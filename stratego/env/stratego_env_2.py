# In stratego_env_2

# Import the 'textarena' library and give it the short alias 'ta'
import textarena as ta
# Import the 'sys' library, which gives access to system functions (like exiting the script)
import sys

# --- REGISTRATION ---

# From the textarena library, import the 'register' and 'check_env_exists' functions
from textarena.envs.registration import register, check_env_exists

# From your local project, import the 'StrategoDuelEnv' class
# This assumes the file is at: stratego/env/StrategoDuel/env.py
from stratego.env.StrategoDuel.env import StrategoDuelEnv 

# --- RUNTIME REGISTRATION ---
# This 'if' block runs *once* when this file is imported

# Check if an environment with the ID "Stratego-duel" is NOT already registered
try:
    # Try to register the environment
    # If not, print a message to the console so we know it's working
    print("--- Registering custom environment 'Stratego-duel' ---")
    # Call textarena's 'register' function to make it aware of our new game
    register(
        # This is the unique string ID we will use to call our game
        id="Stratego-duel",
        # This tells textarena which class to load when it sees the ID
        entry_point=StrategoDuelEnv, 
        # This re-uses the standard textarena wrappers for board games
        wrappers=ta.envs.BOARDGAME_WRAPPERS 
    )
except ValueError:
    # If it fails with a ValueError (already registered), just pass
    print("--- Custom environment 'Stratego-duel' is already registered. ---")
    pass

# --- CLASS DEFINITION ---

# Define a new class (a 'blueprint' for an object) named StrategoEnv
class StrategoEnv:
    """
    (This is a docstring, which explains what the class does)
    A smart wrapper that can load both "Stratego-v0"
    and our custom "Stratego-duel" environment.
    """
    
    # Define the constructor (the function that runs when you create a new StrategoEnv object)
    # 'env_id' is a string argument, '**rule_opts' collects any other optional arguments
    def __init__(self, env_id: str = "Stratego-v0", **rule_opts):
        # Print a status message to the console
        print(f"--- Attempting to create environment: '{env_id}' ---")
        # Start a 'try' block to catch errors if 'ta.make' fails
        try:
            # Call the textarena 'make' function with the 'env_id' we received
            # 'self.env' becomes a variable holding the actual game object
            self.env = ta.make(env_id=env_id)
            # (These are just your comments, they don't do anything)
            # --- THIS IS THE UPDATED LINE ---
            # ---
            
            # If the 'try' block succeeded, print a success message
            print(f"SUCCESS: Successfully created '{env_id}'")
            # Print the text representation of the game object for debugging
            print(f"   Env object: {self.env}\n")
            
        # 'except' catches any 'Exception' (error) that happened in the 'try' block
        except Exception as e:
            # Print a clear failure message
            print(f"!!!!!!!! FAILED to create '{env_id}' !!!!!!!!")
            # Print the actual error 'e' that Python reported
            print(f"Error: {e}")
            # Exit the entire script with an error code (1) because we can't continue
            sys.exit(1)
            
    # Define a method (a function inside a class) called 'reset'
    def reset(self, num_players: int = 2):
        # Print a status message
        print(f"--- Resetting {self.env.env_id} ---")
        # Call the 'reset' method of the *inner* textarena game object
        return self.env.reset(num_players=num_players) 

    # Define a method to get the current game state
    def get_observation(self):
        # Call the 'get_observation' method of the inner game object
        return self.env.get_observation()

    # Define a method to take a game turn (a 'step')
    def step(self, action: str):
        # Call the 'step' method of the inner game object
        return self.env.step(action=action)

    # Define a method to clean up at the end of the game
    def close(self):
        # Call the 'close' method of the inner game object
        return self.env.close()