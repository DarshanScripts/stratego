import textarena as ta
import sys

# This is the class from your todo list
class StrategoEnv:
    def __init__(self, env_id: str = "Stratego-v0", **rule_opts):
        print(f"--- Attempting to create environment: '{env_id}' ---")
        try:
            # This 'ta.make' is what we fixed!
            self.env = ta.make(env_id=env_id)
            print(f"SUCCESS: Successfully created '{env_id}'")
            print(f"   Env object: {self.env}\n")
        except Exception as e:
            print(f"!!!!!!!! FAILED to create '{env_id}' !!!!!!!!")
            print(f"Error: {e}")
            print("Please double-check your __init__.py registration.")
            sys.exit(1) # Exit the script if it fails
            
    # (You can add your other class functions here like reset, step, etc.)

# --- This is the part that will run ---
if __name__ == "__main__":
    
    # Test 1: Load the original Stratego
    env_original = StrategoEnv(env_id="Stratego-v0")
    
    # Test 2: Load your new Stratego-duel
    env_duel = StrategoEnv(env_id="Stratego-duel")
    
    print("--- Test Complete: Both environments loaded successfully! ---")