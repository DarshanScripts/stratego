# In check_duel.py

# Import the class from your stratego_env.py file
from stratego_env_1 import StrategoEnv

print("==============================================")
print("TEST 1: LOADING ORIGINAL STRATEGO (Stratego-v0)")
print("==============================================")

# 1. Create the original game

env_original = StrategoEnv(env_id="Stratego-v0")

# 2. Start the game
env_original.reset(num_players=2)

# 3. Get the starting observation (the board)
obs_original = env_original.get_observation()
print("\n--- ORIGINAL GAME: STARTING OBSERVATION ---")
print(obs_original[1])


print("\n\n==============================================")
print("TEST 2: LOADING STRATEGO DUEL (Stratego-duel)")
print("==============================================")

# 1. Create the duel game

env_duel = StrategoEnv(env_id="Stratego-duel")

# 2. Start the game
env_duel.reset(num_players=2)

# 3. Get the starting observation (the board)
obs_duel = env_duel.get_observation()
print("\n--- DUEL GAME: STARTING OBSERVATION ---")
print(obs_duel[1])

print("\n\n--- TEST COMPLETE ---")
print("Are the two observations above different?")