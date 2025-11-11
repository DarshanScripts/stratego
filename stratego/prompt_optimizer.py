import os
import json
import glob
from stratego.models.ollama_model import OllamaAgent

# ----------------------------
# Reads the last games
# ----------------------------
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

# ----------------------------
# Optimizez the prompt based on the info in logs
# ----------------------------
def improve_prompt(log_dir: str, output_path: str, model_name: str = "mistral:7b"):
    print("🧪 Testing prompt improvement manually...")

    games = load_last_games(log_dir)
    if not games:
        print("ℹ️ Only 0 games logged, skipping prompt improvement.")
        return

    # Writes the raw output for the analysis
    summaries_path = os.path.join(os.path.dirname(output_path), "game_summaries.json")
    with open(summaries_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)
    print(f"💾 Saved raw game summaries to {summaries_path}")

    # Reades the old prompt if it exists
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            old_prompt = f.read().strip()
    else:
        old_prompt = "You are a Stratego-playing AI agent. Output one legal move in format [A0 B0]."

    # Creates the instance for the llm model
    llm = OllamaAgent(model_name=model_name)

    # Creates the prompt for the llm
    analysis_prompt = f"""
You are a Stratego prompt optimizer AI.

Below is the current system prompt:
---
{old_prompt}
---

Here are summaries of the last {len(games)} games (models, moves, prompts, etc.):
{json.dumps(games, indent=2)[:4000]}

Based on these patterns:
- Make the Stratego agent play smarter and less repetitive.
- Encourage better capture or defensive behavior.
- Keep output concise and always in format [SRC DST].
- Return ONLY the new improved prompt text, no JSON, no explanations.
"""

    print("🧠 Sending optimization request to LLM...")
    improved = llm._llm_once(analysis_prompt)

    # 🔄 Fallback in case the model does not respond
    if not improved or improved.strip() == "":
        print("⚠️ No response from Ollama — using fallback improved prompt.")
        improved = """You are an improved Stratego AI.
Analyze the board logically and play proactively.
Prefer moves that capture or pressure enemy pieces.
Output exactly one legal move in the format [SRC DST]."""

    # Writes the final prompt
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(improved.strip())

    print("✅ Prompt updated successfully.\n")
    print("🧠 NEW PROMPT:\n" + "-" * 60)
    print(improved.strip())
    print("-" * 60)

# ----------------------------
# Direct execution
# ----------------------------
if __name__ == "__main__":
    improve_prompt("logs", "stratego/prompts/current_prompt.txt", model_name="phi3:mini")
