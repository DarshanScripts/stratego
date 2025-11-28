import ollama
import re
import random
import statistics
from dataclasses import dataclass


# --- Définition du PromptPack ---
@dataclass
class PromptPack:
    name: str
    system: str
    guidance_template: str

    def build_prompt(self, board_slice: str) -> str:
        return f"{self.system}\n\n{self.guidance_template.format(board_slice=board_slice)}"


# --- Variantes de prompts Stratégo ---
PROMPTS = [
    PromptPack(
        "base",
        "You are a Stratego-playing AI. Output exactly one move [SRC DST].",
        "{board_slice}\nPick one move from 'Available Moves:' and avoid 'FORBIDDEN:'.",
    ),
    PromptPack(
        "aggressive",
        "You are a Stratego AI that favors attacks and forward advancement.",
        "{board_slice}\nChoose an aggressive move from 'Available Moves:' but avoid 'FORBIDDEN:'.",
    ),
    PromptPack(
        "defensive",
        "You are a defensive Stratego AI. Prefer safe and backward moves.",
        "{board_slice}\nPick one safe move and avoid 'FORBIDDEN:'.",
    ),
    PromptPack(
        "adaptive",
        "You are an expert Stratego AI. Balance offense and defense smartly.",
        "{board_slice}\nChoose one optimal move considering both safety and progress. Avoid 'FORBIDDEN:'.",
    ),
]


# --- Fonctions utilitaires ---
def extract_moves(board_slice: str):
    available_line = next((l for l in board_slice.splitlines() if "Available Moves:" in l), "")
    forbidden_line = next((l for l in board_slice.splitlines() if "FORBIDDEN:" in l), "")
    available = re.findall(r"\[[A-Z][0-9] [A-Z][0-9]\]", available_line)
    forbidden = re.findall(r"\[[A-Z][0-9] [A-Z][0-9]\]", forbidden_line)
    return available, forbidden


def is_valid_move(move: str, available: list, forbidden: list):
    return move in available and move not in forbidden


def query_ollama(model: str, prompt: str) -> str:
    try:
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        text = response["message"]["content"]
        match = re.search(r"\[[A-Z][0-9] [A-Z][0-9]\]", text)
        return match.group(0) if match else "INVALID"
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return "INVALID"


# --- Simulation de plusieurs tours ---
def generate_board_slices(num_rounds=5):
    letters = ["A", "B", "C", "D", "E", "F"]
    boards = []
    for _ in range(num_rounds):
        available = [f"[{random.choice(letters)}{random.randint(1,6)} {random.choice(letters)}{random.randint(1,6)}]" for _ in range(4)]
        forbidden = random.sample(available, k=random.randint(0, 1))
        board_slice = f"Available Moves: {', '.join(available)}\nFORBIDDEN: {', '.join(forbidden)}"
        boards.append(board_slice)
    return boards


# --- Évaluation multi-turn ---
def evaluate_prompts_multiturn(model: str, num_rounds=5):
    boards = generate_board_slices(num_rounds)
    scores = {p.name: [] for p in PROMPTS}

    print(f"\n Starting evaluation on {num_rounds} rounds with model: {model}\n")

    for round_idx, board_slice in enumerate(boards, start=1):
        available, forbidden = extract_moves(board_slice)
        print(f"\n===== ROUND {round_idx} =====")
        print(board_slice)

        for pack in PROMPTS:
            prompt_text = pack.build_prompt(board_slice)
            move = query_ollama(model, prompt_text)
            valid = is_valid_move(move, available, forbidden)
            scores[pack.name].append(1 if valid else 0)
            print(f"→ {pack.name.upper():<10} | Move: {move:<10} | Valid: {valid}")

    # --- Résumé global ---
    print("\n === FINAL RESULTS ===")
    for name, result_list in scores.items():
        avg = statistics.mean(result_list)
        print(f"{name.capitalize():<10}: {sum(result_list)}/{len(result_list)} valid moves ({avg*100:.1f}%)")

    best_prompt = max(scores.items(), key=lambda x: statistics.mean(x[1]))[0]
    print(f"\n Best performing prompt: {best_prompt.upper()}")
    return scores


# --- Lancer le test ---
#if __name__ == "__main__":
   # evaluate_prompts_multiturn("gemma:2b", num_rounds=5)
