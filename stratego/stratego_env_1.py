# In stratego_env_1.py

import textarena as ta
import sys

class StrategoEnv:
    def __init__(self, env_id: str = "Stratego-v0", **rule_opts):
        print(f"--- Attempting to create environment: '{env_id}' ---")
        try:
            # --- THIS IS THE UPDATED LINE ---
            self.env = ta.make(env_id=env_id)
            # ---
            
            print(f"SUCCESS: Successfully created '{env_id}'")
            print(f"   Env object: {self.env}\n")
            
        except Exception as e:
            print(f"!!!!!!!! FAILED to create '{env_id}' !!!!!!!!")
            print(f"Error: {e}")
            sys.exit(1)
            
    def reset(self, num_players: int = 2):
        print(f"--- Resetting {self.env.env_id} ---")
        # Call the underlying environment's reset
        return self.env.reset(num_players=num_players) 

    def get_observation(self):
        return self.env.get_observation()

    def step(self, action: str):
        return self.env.step(action=action)

    def close(self):
        return self.env.close()
