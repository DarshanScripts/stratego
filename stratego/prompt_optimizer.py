import os
import json
import glob
from stratego.models.ollama_model import OllamaAgent

# Reads the last games
def load_last_games(log_dir: str, limit: int = 10):
    games = []
    csv_files = sorted(glob.glob(os.path.join(log_dir, "*.csv")), reverse=True)
    for path in csv_files[:limit]:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        moves = [ln.strip().split(",") for ln in lines if ln.startswith(tuple("202"))]

        models = {}
        prompts = {}
        example_moves = []

        for parts in moves:
            if len(parts) < 4:
                continue
            if parts[2] == "prompt":
                player, model = parts[3], parts[4]
                text = parts[6]
                prompts[player] = text
                models[player] = model
            elif parts[2] == "move" and len(example_moves) < 10:
                example_moves.append(parts[8])

        games.append({
            "file": os.path.basename(path),
            "models": models,
            "initial_prompts": prompts,
            "num_moves": len([m for m in moves if len(m) > 2 and m[2] == "move"]),
            "example_moves": example_moves
        })
    return games

# Optimizez the prompt based on the info in logs
def improve_prompt(log_dir: str, output_path: str, model_name: str = "mistral:7b"):
    print("Testing prompt improvement manually...")

    games = load_last_games(log_dir)
    if not games:
        print("Only 0 games logged, skipping prompt improvement.")
        return

    # Writes the raw output for the analysis
    summaries_path = os.path.join(os.path.dirname(output_path), "game_summaries.json")
    with open(summaries_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)
    print(f"Saved raw game summaries to {summaries_path}")

    # Reades the old prompt if it exists
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            old_prompt = f.read().strip()
    else:
        old_prompt = "You are an expert Stratego-playing AI agent.\nYour goal is to win the game by strategically capturing the opponent's flag or eliminating all movable enemy pieces.\nFollow these instructions carefully:\n\n1. Rules of Movement\n- You can move one piece per turn.\n- Pieces move one square per turn, horizontally or vertically (no diagonals).\n- You cannot move onto lakes or outside the board.\n- Bombs (B) and Flags (F) cannot move.\n\n2. Attacking Rules\n- When moving onto a square occupied by an opponent's piece:\n  - The lower-ranked piece loses.\n  - If ranks are equal, both pieces are removed.\n  - The Spy (1) can defeat the Marshal (10) only if the Spy attacks first.\n  - The Miner (3) can defuse Bombs (B).\n\n3. Strategic Guidelines\n- Prioritize discovering unknown enemy pieces.\n- Protect your Flag and high-value pieces such as the Marshal and General.\n- Use Scouts (9) to explore open lines.\n- Use Miners (3) to disarm Bombs when possible.\n- Avoid repetitive or meaningless moves.\n- Maintain a balance between attack and defense.\n- Try to gain information about enemy positions while minimizing risk.\n\n4. Output Format\n- Always output exactly one legal move using the format: [SRC DST]\n  Example: [D5 E5]\n\n5. Constraints\n- Do not output any explanations, reasoning, or additional text.\n- If multiple moves are possible, choose the one that maximizes long-term strategic advantage.\n\nExample of correct output:\n[D4 E4]\n\nYou are now playing Stratego as an intelligent and strategic agent. Think ahead, adapt, and play to win."

    # Creates the instance for the llm model
    llm = OllamaAgent(model_name=model_name)

    # Creates the prompt for the llm
    analysis_prompt = f"""
You are a Stratego prompt optimizer AI responsible for refining the Stratego-playing agent's system prompt.

Below is the current system prompt:
---
{old_prompt}
---

Here are summaries of the last {len(games)} games (models, moves, prompts, outcomes, and any identified issues):
{json.dumps(games, indent=2)[:4000]}
---

Your task:
- Produce a single improved Stratego system prompt that keeps the correct game rules, especially:
  * Orthogonal one-square movement (no diagonals)
  * Scouts (9) move any number of squares in a straight line
  * Bombs (B) and Flags (F) are immobile
  * Spy (1) can defeat Marshal (10) only if the Spy attacks
  * Miner (3) defuses Bombs
- Reinforce the output contract: output **exactly one legal move** in the format `[SRC DST]` and **nothing else**.
- Strengthen adaptive strategic reasoning:
  * Prioritize smart captures, cautious defense, and minimizing repetition.
  * Balance offense and defense; protect key pieces while seeking high-value captures.
  * Learn from previous moves and avoid repetitive back-and-forth sequences.
- If multiple moves are possible, prefer those that yield long-term advantage (positional or informational).
- Include clear rules, strategy, and output format sections in the final text.
- Keep the language concise and instructional.
- Return **only** the new improved Stratego system prompt text in single line format using \n (no JSON, no commentary, no extra lines outside the prompt).
- Add the problems found in the previous prompt to be fixed in the new prompt. Add them below in the "Known Issues" section.

Known Issues with the current prompt:
1. Some games showed repetitive move patterns leading to stalemates.

Output strictly:
A single coherent Stratego system prompt ready to be used by the game-playing LLM.
"""


    print("Sending optimization request to LLM...")
    improved = llm._llm_once(analysis_prompt)

    # Fallback in case the model does not respond
    if not improved or improved.strip() == "":
        print("No response from Ollama — using fallback improved prompt.")
        improved = """You are an improved Stratego AI.
Analyze the board logically and play proactively.
Prefer moves that capture or pressure enemy pieces.
Output exactly one legal move in the format [SRC DST]."""

    # Writes the final prompt
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(improved.strip())

    print("Prompt updated successfully.\n")
    print("NEW PROMPT:\n" + "-" * 60)
    print(improved.strip())
    print("-" * 60)

# Direct execution
if __name__ == "__main__":
    improve_prompt("./stratego/logs", "stratego/prompts/current_prompt.txt", model_name="mistral:7b")