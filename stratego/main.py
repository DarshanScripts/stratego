import argparse
#updated import statement
from stratego.env.stratego_env_2 import StrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines

#Revised to set temperature(13 Nov 2025)
def build_agent(spec: str, prompt_name: str):
    kind, name = spec.split(":", 1)
    if kind == "ollama":
        # Define the temperature value explicitly
        AGENT_TEMPERATURE = 0.2
        
        # OllamaAgent holds the model_name, temperature, and prompt_pack
        agent = OllamaAgent(model_name=name, temperature=AGENT_TEMPERATURE, num_predict=32,
                            prompt_pack=get_prompt_pack(prompt_name))
        
        # FIX: Attach the temperature attribute to the agent object so it can be logged later
        agent.temperature = AGENT_TEMPERATURE
        
        return agent
    raise ValueError(f"Unknown agent spec: {spec}")

# Later we can make printing board method as more in detail.
def print_board(observation: str):
    block = extract_board_block_lines(observation)
    if block:
        # Print a separator for readability(13 Nov 2025)
        print("\n" + "="*50)
        print("\n".join(block))

# With those arguments, user can change game setting
def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:mistral:7b")
    p.add_argument("--p1", default="ollama:gemma:2b")

    # UPDATED HELP TEXT to explain how this parameter relates to VRAM utilization
    # For large models (120B, 70B), you MUST set this value based on available VRAM(13 Nov 2025)
    # UPDATED GPU arguments for VRAM control (now defaults to CPU-only)
    p.add_argument("--p0-num-gpu", type=int, default=0,
                    help="Number of GPU layers to offload for Player 0. Default is 0 (CPU-only mode). Use a positive number (e.g., 50) to offload layers to GPU/VRAM, or 999 for maximum GPU use.")
    p.add_argument("--p1-num-gpu", type=int, default=0,
                    help="Number of GPU layers to offload for Player 1. Default is 0 (CPU-only mode). Use a positive number (e.g., 40) to offload layers to GPU/VRAM, or 999 for maximum GPU use.")
    
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--env_id", default="Stratego-v0", help="TextArena environment id")
    args = p.parse_args()

  # Agents initialization
    agents = {
        0: build_agent(args.p0, args.prompt),
        1: build_agent(args.p1, args.prompt),
    }
    env = StrategoEnv(env_id=args.env_id)
    env.reset(num_players=2)

    done = False

    #Turn Counter Initialization(13 Nov 2025)

    turn_count = 0  # Initialize turn counter

    print("\n--- Stratego LLM Match Started ---")
    print(f"Player 0 Agent: {agents[0].model_name} (Prompt: {args.prompt})")
    print(f"Player 1 Agent: {agents[1].model_name} (Prompt: {args.prompt})\n")

    #Whole block revised(13 Nov 2025)
    while not done:
        turn_count += 1
        player_id, observation = env.get_observation()
        
        # Determine agent name and details for current player
        current_agent = agents[player_id]
        player_display = f"Player {player_id}"
        model_name = current_agent.model_name
        
        # --- NEW LOGGING FOR TURN, PLAYER, AND MODEL ---
        print(f"\n>>>> TURN {turn_count}: {player_display} ({model_name}) is moving...")
        print_board(observation)
        
        # The agent (LLM) generates the action
        action = current_agent(observation)
        
        # --- NEW LOGGING FOR STRATEGY/MODEL DECISION ---
        print(f"  > AGENT DECISION: {model_name} -> {action}")
        print(f"  > Strategy/Model: Ollama Agent (T={current_agent.temperature}, Prompt='{args.prompt}')")

        # Step the environment
        done, _ = env.step(action=action)

    rewards, game_info = env.close()
    print("\n" + "="*50)
    print("--- GAME OVER ---")
    print(f"Final Rewards: {rewards}")
    print(f"Game Info: {game_info}")

if __name__ == "__main__":
    cli()