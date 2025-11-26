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
        
        # Parse CSV properly
        import csv
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        models = {}
        prompts = {}
        example_moves = []
        detailed_moves = []
        invalid_moves = []
        repeated_moves = []
        piece_usage = {}
        battle_results = {"won": 0, "lost": 0, "draw": 0}

        for row in rows:
            if row.get("type") == "prompt":
                player = row.get("player")
                model = row.get("model_name")
                text = row.get("prompt", "")
                prompts[player] = text
                models[player] = model
            elif row.get("type") == "move":
                move = row.get("move", "")
                piece_type = row.get("piece_type", "")
                outcome = row.get("outcome", "")
                captured = row.get("captured", "")
                was_repeated = row.get("was_repeated", "no")
                
                if len(example_moves) < 10:
                    example_moves.append(move)
                
                detailed_moves.append({
                    "move": move,
                    "piece": piece_type,
                    "outcome": outcome,
                    "captured": captured,
                    "repeated": was_repeated
                })
                
                if outcome == "invalid":
                    invalid_moves.append({"piece": piece_type, "move": move})
                
                if was_repeated == "yes":
                    repeated_moves.append({"piece": piece_type, "move": move})
                
                if piece_type:
                    piece_usage[piece_type] = piece_usage.get(piece_type, 0) + 1
                
                if "won" in outcome:
                    battle_results["won"] += 1
                elif "lost" in outcome:
                    battle_results["lost"] += 1
                elif "draw" in outcome:
                    battle_results["draw"] += 1

        total_moves = len([m for m in detailed_moves if m.get("outcome")])
        games.append({
            "file": os.path.basename(path),
            "models": models,
            "initial_prompts": prompts,
            "num_moves": total_moves,
            "example_moves": example_moves,
            "detailed_moves": detailed_moves[:10],  # First 10 for analysis
            "invalid_count": len(invalid_moves),
            "invalid_rate": len(invalid_moves) / max(total_moves, 1),
            "repeated_count": len(repeated_moves),
            "repeat_rate": len(repeated_moves) / max(total_moves, 1),
            "piece_usage": piece_usage,
            "battle_results": battle_results,
            "invalid_moves": invalid_moves[:5],  # Top 5 for analysis
            "repeated_moves": repeated_moves[:5]
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

    # Analyze common issues across games
    total_invalid = sum(g.get("invalid_count", 0) for g in games)
    total_repeated = sum(g.get("repeated_count", 0) for g in games)
    avg_invalid_rate = sum(g.get("invalid_rate", 0) for g in games) / max(len(games), 1)
    avg_repeat_rate = sum(g.get("repeat_rate", 0) for g in games) / max(len(games), 1)
    
    # Collect common mistake patterns
    all_invalid = []
    all_repeated = []
    for g in games:
        all_invalid.extend(g.get("invalid_moves", []))
        all_repeated.extend(g.get("repeated_moves", []))
    
    issue_summary = f"""
### STATISTICS FROM LAST {len(games)} GAMES:
- Average Invalid Move Rate: {avg_invalid_rate*100:.1f}%
- Average Repeat Move Rate: {avg_repeat_rate*100:.1f}%
- Total Invalid Moves: {total_invalid}
- Total Repeated Moves: {total_repeated}

### COMMON MISTAKES:
Invalid Moves: {json.dumps(all_invalid[:5], indent=2)}
Repeated Moves: {json.dumps(all_repeated[:5], indent=2)}
"""

    # Creates the prompt for the llm
    analysis_prompt = f"""
You are a Stratego prompt optimizer AI responsible for refining the Stratego-playing agent's system prompt.

Below is the current system prompt:
---
{old_prompt}
---

{issue_summary}

Here are detailed summaries of the last {len(games)} games:
{json.dumps(games, indent=2)[:3000]}
---

Your task:
- DO NOT rewrite or replace the current prompt entirely.
- Instead, carefully **append or modify** sections of the old prompt only where logically needed.
- Preserve all original sections, wordings, and formatting of old_prompt.
- Append new clarifications or improvements **after** the existing text in a section called "Prompt Enhancements:".
- Keep every original rule intact (do not delete or reword existing ones).
- Add any new fixes only at the end under "Prompt Enhancements:" followed by numbered improvements.
- Focus on fixing the specific issues identified in the statistics above.
- If certain pieces (like Bombs) generate many invalid moves, add explicit rules about them.
- If repeated moves are common, add stronger warnings against repeating recent moves.
- Never remove or reformat the old prompt content.
- Keep all \n as literal line breaks for readability.
- The final output must contain:
  1. The full old prompt text (unchanged)
  2. An added "Prompt Enhancements:" section containing:
     - fixes for known issues from recent games
     - any additional clarity or constraints to improve performance
- Output exactly the final updated prompt text, no commentary or explanation.
- Return in a single text block (no JSON).

Prompt Enhancements:
1. Address the {avg_invalid_rate*100:.1f}% invalid move rate with explicit rules.
2. Reduce the {avg_repeat_rate*100:.1f}% repeat rate by emphasizing move diversity.
3. Add specific tactical advice based on piece usage patterns.


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
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(improved.strip())

    print("Prompt updated successfully.\n")
    print("NEW PROMPT:\n" + "-" * 60)
    print(improved.strip())
    print("-" * 60)

# Direct execution
if __name__ == "__main__":
    improve_prompt("logs", "stratego/prompts/current_prompt.txt", model_name="phi3:14b")