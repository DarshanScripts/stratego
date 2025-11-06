import argparse
from stratego.env.stratego_env import StrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack
from stratego.utils.parsing import extract_board_block_lines

from stratego.strategies.aggressive_strategy import AggressiveStrategy
from stratego.strategies.defensive_strategy import DefensiveStrategy
from stratego.strategies.random_move import RandomStrategy


def build_agent(spec: str,  prompt_name: str, strategy_name: str):
    kind, name = spec.split(":", 1)
    
        # Choose strategy
    strategy_map = {
        "aggressive": AggressiveStrategy(),
        "defensive": DefensiveStrategy(),
        "random": RandomStrategy(),
    }
    strategy = strategy_map.get(strategy_name, RandomStrategy())
    
    if kind == "ollama":
        return OllamaAgent(
                    model_name=name,
                    temperature=0.2,
                    num_predict=32,
                    prompt_pack=get_prompt_pack(prompt_name),
                    strategy=strategy,
                )
    raise ValueError(f"Unknown agent spec: {spec}")

# Later we can make printing board method as more in detail.
def print_board(observation: str):
    block = extract_board_block_lines(observation)
    if block:
        print("\n".join(block))

# With those arguments, user can change game setting
def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:gemma3:270m")
    p.add_argument("--p1", default="ollama:qwen2.5:0.5b")
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--env_id", default="Stratego-v0", help="TextArena environment id")
    p.add_argument("--s0", default="aggressive", help="Strategy for player 0")
    p.add_argument("--s1", default="defensive", help="Strategy for player 1")   
    args = p.parse_args()

    agents = {
    0: build_agent(args.p0, args.prompt, args.s0),
    1: build_agent(args.p1, args.prompt, args.s1),
    }
   
    env = StrategoEnv(env_id=args.env_id)
    env.reset(num_players=2)

    done = False
    step_count = 0
    max_steps = 50
    
    while not done and step_count < max_steps:
        player_id, observation = env.get_observation()
        print_board(observation)

        action = agents[player_id](observation)
        print(f"{agents[player_id].model_name} -> {action}")

        done, _ = env.step(action=action)
        step_count += 1

    print(f"Game stopped after {step_count} steps.")
    rewards, game_info = env.close()
    print("Game finished.", rewards, game_info)


if __name__ == "__main__":
    cli()
