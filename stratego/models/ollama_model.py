import os
import random
import re
from typing import Optional
from langchain_ollama import ChatOllama
import requests

from .base import AgentLike
from ..utils.parsing import (
    extract_legal_moves, slice_board_and_moves, strip_think, MOVE_RE
)

# I seperated Prompts from the code
from ..prompts import PromptPack, get_prompt_pack

class OllamaAgent(AgentLike):
    def __init__(
        self,
        model_name: str,
        system_prompt: Optional[str] = None,
        host: Optional[str] = None,
        prompt_pack: Optional[PromptPack | str] = None,
        **kwargs,
    ):
        self.model_name = model_name
        self.STRATEGIC_GUIDANCE = """
You are a skilled Stratego player. You must choose the SINGLE best legal move from the given board, legal moves, forbidden moves, and move history.

GENERAL RULES:
1. Output EXACTLY ONE MOVE in the form [A0 B0].
2. NEVER output explanations, commentary, or reasoning.
3. Try to choose a move that would be legal in Stratego rules.
4. NEVER repeat a previous move unless it creates a tactical advantage (capture, reveal, escape).
5. AVOID back-and-forth oscillations (e.g., A5->A6 then A6->A5).
6. It would be considered a SERIOUS MISTAKE, which leads you to lose the game, to attempt illegal moves such as moving a Flag or Bomb, moving in an impossible way, moving upon its own pieces, or trying to move opponent's pieces.

STRATEGIC PRINCIPLES:
1. Avoid random or pointless shuffling of pieces.
2. Prefer moves that improve board position, uncover information, or apply pressure.
3. Avoid moving high-value officers (Marshal, General, Colonel) blindly into unknown pieces.
4. Prefer advancing Scouts for reconnaissance.
5. Avoid moving bombs unless revealed and forced.
6. Do NOT walk pieces next to the same unknown piece repeatedly without purpose.
7. Do NOT afraid to sacrifice low-rank pieces for information gain.

CAPTURE & SAFETY RULES:
1. If you can capture a known weaker enemy piece safely, prefer that move.
2. NEVER attack a higher-ranked or unknown piece with a valuable piece unless strategically justified.
3. If the enemy piece is revealed as weaker, press the advantage.
4. If your piece is threatened, retreat or reposition instead of repeating the last move.

USE OF HISTORY:
1. Avoid repeating cycles recognized in the history (e.g., A->B->A->B).
2. Track revealed enemy pieces from history and use rank knowledge:
   - If they moved, they are not Bombs or Flags.
   - If they captured, infer their rank and avoid attacking with weaker pieces.
3. If an enemy repeatedly retreats from your piece, continue safe pressure.

POSITIONING RULES:
1. Advance pieces that have strategic value while keeping your formation stable.
2. Keep bombs guarding high-value territory; avoid unnecessary bomb movement.
3. Push on flanks where the opponent retreats often.
4. Maintain escape squares for your high-ranking leaders.

ENDGAME LOGIC:
1. Prioritize discovering and attacking the opponent's flag location.
2. Secure safe paths for Miners to remove bombs.
3. In endgame, prioritize mobility and avoid blockades caused by your own pieces.

CHOOSE THE BEST MOVE:
Evaluate all legal moves and pick the one that:
- improves position, OR
- pressures an opponent safely, OR
- increases information, OR
- avoids known traps or loops, OR
- ensures safety of valuable pieces.

Output ONLY one legal move in the exact format [A0 B0]. Nothing else.
"""
        if isinstance(prompt_pack, str) or prompt_pack is None:
            self.prompt_pack: PromptPack = get_prompt_pack(prompt_pack)
        else:
            self.prompt_pack = prompt_pack



        if system_prompt is not None:
            self.system_prompt = system_prompt
        else:
            # if there is already an existing updated prompt, we use that one
            prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "current_prompt.txt")
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    self.system_prompt = f.read()
            else:
                self.system_prompt = self.prompt_pack.system
                
                
        self.initial_prompt = self.system_prompt

        base_url = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model_kwargs = {
            "temperature": kwargs.pop("temperature", 0.1),
            "top_p": kwargs.pop("top_p", 0.9),
            "repeat_penalty": kwargs.pop("repeat_penalty", 1.05),
            "num_predict": kwargs.pop("num_predict", 24),
            **kwargs,
        }
        self.client = ChatOllama(model=model_name, base_url=base_url, model_kwargs=model_kwargs)
        
        # Simple move history tracking
        self.move_history = []
        self.player_id = None

    def set_move_history(self, history):
        """Set the recent move history for this agent."""
        self.move_history = history

    def _llm_once(self, prompt: str) -> str:
        """Send request directly to Ollama REST API (fixes Windows LangChain bug)."""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )
            if response.status_code == 200:
                data = response.json()
                return (data.get("response") or "").strip()
            else:
                print(f"Ollama returned HTTP {response.status_code}: {response.text}")
                return ""
        except Exception as e:
            print(f"Ollama request failed: {e}")
            return ""

    def __call__(self, observation: str) -> str:
        # Build context
        slim = slice_board_and_moves(observation)

        prompt_history_lines = []
        for line in observation.splitlines():
            if line.startswith("Turn ") or "played[" in line:
                prompt_history_lines.append(line)
        history = "\n".join(prompt_history_lines)
        full_context = slim + ("\n\nMOVE HISTORY:\n" + history if history else "")

        # >>> THE CRITICAL FIX <<<
        guidance = (
            self.STRATEGIC_GUIDANCE
            + "\n\n"
            + self.prompt_pack.guidance(full_context)
        )

        recent_moves = set()
        if len(self.move_history) >= 2:
            recent_moves = {m["move"] for m in self.move_history[-2:]}
        
        last_error = None
        BARE_MOVE_RE = re.compile(r"\b([A-J]\d)\s+([A-J]\d)\b")
        # Now the model ALWAYS sees your anti-repeat rules
        for _ in range(4):
            raw = self._llm_once(guidance)
            if not raw:
                last_error = "empty response (timeout or HTTP error)"
                continue
            
            m = MOVE_RE.search(raw)
            if m:
                mv = m.group(0)
            else:
                m2 = BARE_MOVE_RE.search(raw)
                if m2:
                    src = m2.group(1)
                    dst = m2.group(2)
                    mv = f"[{src} {dst}]"
                else:
                    last_error = f"no move found in response: {raw[:80]!r}"
                    continue
            
            # Check if it's a repeat of recent move
            if mv in recent_moves and len(recent_moves) > 0:
                last_error = f"repeated move {mv}"
                if _ < 3:
                    print(f"   LLM proposed recent move {mv}, trying alternatives...")
                    continue
                else:
                    print(f"   LLM keeps proposing {mv}; accepting it on final attempt.")
                    return mv
            
            return mv
        
        # if last_raw:
        #     candidates = MOVE_RE.findall(last_raw)
        #     if candidates:
        #         non_recent = [mv for mv in candidates if mv not in recent_moves]
        #         if non_recent:
        #             return non_recent[0]
        #         return candidates[0]
        
        # obs_moves = MOVE_RE.findall(observation)
        # if obs_moves:
        #     non_recent = [mv for mv in obs_moves if mv not in recent_moves]
        #     if non_recent:
        #         return random.choice(non_recent)
        #     return random.choice(obs_moves)
        
        print(f"[AGENT] {self.model_name} failed to produce valid move after retries.")
        if last_error:
            print(f"   Last error: {last_error}")
        
        legal = extract_legal_moves(observation)
        return random.choice(legal)