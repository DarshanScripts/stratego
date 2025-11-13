import os, random
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from .base import AgentLike
from ..utils.parsing import (
    extract_legal_moves, extract_forbidden, slice_board_and_moves, strip_think, MOVE_RE
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
3. ONLY choose moves that appear in the legal moves list.
4. NEVER repeat a previous move unless it creates a tactical advantage (capture, reveal, escape).
5. AVOID back-and-forth oscillations (e.g., A5->A6 then A6->A5).

STRATEGIC PRINCIPLES:
1. Avoid random or pointless shuffling of pieces.
2. Prefer moves that improve board position, uncover information, or apply pressure.
3. Avoid moving high-value officers (Marshal, General, Colonel) blindly into unknown pieces.
4. Prefer advancing Scouts for reconnaissance.
5. Avoid moving bombs unless revealed and forced.
6. Do NOT walk pieces next to the same unknown piece repeatedly without purpose.

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

        self.system_prompt = system_prompt if system_prompt is not None else self.prompt_pack.system
        self.initial_prompt = self.system_prompt

        base_url = host or os.getenv("OLLAMA_HOST", "http://localhost:11437")
        model_kwargs = {
            "temperature": kwargs.pop("temperature", 0.1),
            "top_p": kwargs.pop("top_p", 0.9),
            "repeat_penalty": kwargs.pop("repeat_penalty", 1.05),
            "num_predict": kwargs.pop("num_predict", 24),
            **kwargs,
        }
        self.client = ChatOllama(model=model_name, base_url=base_url, model_kwargs=model_kwargs)

    def _llm_once(self, prompt: str) -> str:
        msgs = [SystemMessage(content=self.system_prompt), HumanMessage(content=prompt)]
        out = self.client.invoke(msgs)
        return strip_think((out.content or "").strip())

    # def __call__(self, observation: str) -> str:
    #     legal = extract_legal_moves(observation)
    #     if not legal:
    #         return ""

    #     forbidden = set(extract_forbidden(observation))
    #     legal_filtered = [m for m in legal if m not in forbidden] or legal[:]
    #     slim = slice_board_and_moves(observation)
    #     guidance = self.prompt_pack.guidance(slim)

    #     for _ in range(4):
    #         raw = self._llm_once(guidance)
    #         m = MOVE_RE.search(raw)
    #         if m:
    #             mv = m.group(0)
    #             if mv in legal_filtered:
    #                 return mv

    #         raw2 = self._llm_once("Output exactly one legal move [A0 B0]. DO NOTE REPEAT MOVES FOR NO STRATEGIG REASON")
    #         m2 = MOVE_RE.search(raw2)
    #         if m2:
    #             mv2 = m2.group(0)
    #             if mv2 in legal_filtered:
    #                 return mv2

    #     return random.choice(legal_filtered)

    # def __call__(self, observation: str) -> str:
    #     legal = extract_legal_moves(observation)
    #     if not legal:
    #         return ""

    #     forbidden = set(extract_forbidden(observation))
    #     legal_filtered = [m for m in legal if m not in forbidden] or legal[:]

    #     # Get board + moves
    #     slim = slice_board_and_moves(observation)

    #     # >>> NEW: extract history directly from observation <<<
    #     # Your tracker appended history to the raw observation earlier
    #     history_lines = []
    #     for line in observation.splitlines():
    #         if line.startswith("Turn ") or "->" in line:
    #             history_lines.append(line)
    #     history = "\n".join(history_lines)

    #     # >>> NEW: Combine slim + history into a single input <<<
    #     full_context = slim
    #     if history.strip():
    #         full_context += "\n\nMOVE HISTORY:\n" + history

    #     # Use combined context in the prompt pack
    #     guidance = self.prompt_pack.guidance(full_context)

    #     # LLM call loop stays identical
    #     for _ in range(4):
    #         raw = self._llm_once(guidance)
    #         m = MOVE_RE.search(raw)
    #         if m:
    #             mv = m.group(0)
    #             if mv in legal_filtered:
    #                 return mv

    #         raw2 = self._llm_once(
    #             self.STRATEGIC_GUIDANCE + "\n\n" + full_context
    #         )
    #         m2 = MOVE_RE.search(raw2)
    #         if m2:
    #             mv2 = m2.group(0)
    #             if mv2 in legal_filtered:
    #                 return mv2

    #     return random.choice(legal_filtered)

    def __call__(self, observation: str) -> str:
        legal = extract_legal_moves(observation)
        if not legal:
            return ""
        forbidden = set(extract_forbidden(observation))
        legal_filtered = [m for m in legal if m not in forbidden] or legal[:]
        # === HARD ANTI-REPEAT RULE ===
        # Detect the last move in history
        raw_history_lines = []
        for line in observation.splitlines():
            if line.startswith("Turn ") and ("played" in line):
                raw_history_lines.append(line)

        last_move = None
        if raw_history_lines:
            # Example line: "Turn 20: You played [A4 A5]"
            last_line = raw_history_lines[-1]
            m = MOVE_RE.search(last_line)
            if m:
                last_move = m.group(0)

        # Filter out moves that are the exact reverse of the last move
        if last_move:
            src = last_move[1:3]      # A4
            dst = last_move[4:6]      # A5
            reverse_move = f"[{dst} {src}]"

            legal_filtered = [
                mv for mv in legal_filtered
                if mv != reverse_move
            ] or legal_filtered

        # Build context
        slim = slice_board_and_moves(observation)

        prompt_history_lines = []
        for line in observation.splitlines():
            if line.startswith("Turn ") or "->" in line:
                prompt_history_lines.append(line)

        history = "\n".join(prompt_history_lines)
        full_context = slim + ("\n\nMOVE HISTORY:\n" + history if history else "")

        # >>> THE CRITICAL FIX <<<
        guidance = (
            self.STRATEGIC_GUIDANCE
            + "\n\n"
            + self.prompt_pack.guidance(full_context)
        )

        # Now the model ALWAYS sees your anti-repeat rules
        for _ in range(4):
            raw = self._llm_once(guidance)
            m = MOVE_RE.search(raw)
            if m:
                mv = m.group(0)
                if mv in legal_filtered:
                    return mv

        # If everything fails, fallback to random
        return random.choice(legal_filtered)
