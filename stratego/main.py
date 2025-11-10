import argparse
from stratego.env.custom_env import CustomStrategoEnv
from stratego.models.ollama_model import OllamaAgent
from stratego.prompts import get_prompt_pack

from stratego.strategies.aggressive_strategy import AggressiveStrategy
from stratego.strategies.defensive_strategy import DefensiveStrategy
from stratego.strategies.random_move import RandomStrategy


# ---------------------- Agent builder ----------------------
def build_agent(spec: str, prompt_name: str, strategy_name: str):
    kind, name = spec.split(":", 1)

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


# ---------------------- Board printing ----------------------
def print_board(observation: str):
    """
    Formatează observația într-o afișare de tip tabel.
    Caută secțiunea 'Board:' și o afișează cu litere + numere.
    """
    lines = observation.splitlines()
    board_lines = []
    start = False
    for line in lines:
        if line.strip().lower().startswith("board"):
            start = True
            continue
        if start:
            if not line.strip():
                break
            board_lines.append(line.strip())

    if not board_lines:
        print(observation)
        return

    n = len(board_lines)
    print("\n    " + "   ".join(str(i) for i in range(len(board_lines[0].split()))))
    for idx, row in enumerate(board_lines):
        print(chr(65 + idx) + "   " + "   ".join(row.split()))
    print()


# ---------------------- Main CLI ----------------------
def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--p0", default="ollama:gemma3:270m")
    p.add_argument("--p1", default="ollama:qwen2.5:0.5b")
    p.add_argument("--prompt", default="base", help="Prompt preset name (e.g. base|concise|adaptive)")
    p.add_argument("--env_id", default="Stratego-v0", help="Environment id")
    p.add_argument("--s0", default="aggressive", help="Strategy for player 0")
    p.add_argument("--s1", default="defensive", help="Strategy for player 1")
    p.add_argument("--size", type=int, default=10, help="Board size (NxN)")
    args = p.parse_args()

    # Creăm agenții
    agents = {
        0: build_agent(args.p0, args.prompt, args.s0),
        1: build_agent(args.p1, args.prompt, args.s1),
    }

    # Inițializăm mediul personalizat
    env = CustomStrategoEnv(env_id=args.env_id, board_size=args.size)
    env.reset(num_players=2)

    done = False
    step_count = 0
    max_steps = 50

    print(f"\n=== Starting Stratego on a {args.size}x{args.size} board ===\n")

    while not done and step_count < max_steps:
        player_id, observation = env.get_observation()

        print_board(observation)

        # Agentul alege o mutare
        action = agents[player_id](observation)
        if not action:
            print(f"{agents[player_id].model_name} -> (no move)")
        else:
            print(f"{agents[player_id].model_name} -> [{action}]")

        # Aplicăm mutarea
        done, _ = env.step(action=action)

        # Afișăm tabla după mutare
        _, new_obs = env.get_observation()
        print_board(new_obs)

        step_count += 1

    print(f"Game stopped after {step_count} steps.")
    rewards, game_info = env.close()
    print("Game finished.", rewards, game_info)


if __name__ == "__main__":
    cli()
