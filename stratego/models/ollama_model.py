import os
import random
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from .base import AgentLike
from ..utils.parsing import (
    extract_legal_moves, extract_forbidden, slice_board_and_moves, strip_think, MOVE_RE
)
from ..prompts import PromptPack, get_prompt_pack

# 🧩 Import strategies
from ..strategies.base import Strategy
from ..strategies.aggressive_strategy import AggressiveStrategy
from ..strategies.defensive_strategy import DefensiveStrategy
from ..strategies.random_move import RandomStrategy


class OllamaAgent(AgentLike):
    def __init__(
        self,
        model_name: str,
        system_prompt: Optional[str] = None,
        host: Optional[str] = None,
        prompt_pack: Optional[PromptPack | str] = None,
        strategy: Optional[Strategy] = None,
        **kwargs,
    ):
        self.model_name = model_name
        self.strategy = strategy or RandomStrategy()  # default dacă nu e setată

        if isinstance(prompt_pack, str) or prompt_pack is None:
            self.prompt_pack: PromptPack = get_prompt_pack(prompt_pack)
        else:
            self.prompt_pack = prompt_pack

        self.system_prompt = system_prompt if system_prompt is not None else self.prompt_pack.system

        base_url = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model_kwargs = {
            "temperature": kwargs.pop("temperature", 0.1),
            "top_p": kwargs.pop("top_p", 0.9),
            "repeat_penalty": kwargs.pop("repeat_penalty", 1.05),
            "num_predict": kwargs.pop("num_predict", 24),
            **kwargs,
        }
        self.client = ChatOllama(model=model_name, base_url=base_url, model_kwargs=model_kwargs)

    # Run one LLM call
    def _llm_once(self, prompt: str) -> str:
        msgs = [SystemMessage(content=self.system_prompt), HumanMessage(content=prompt)]
        out = self.client.invoke(msgs)
        return strip_think((out.content or "").strip())

    # Main decision method
    def __call__(self, observation: str) -> str:
        legal_moves = extract_legal_moves(observation)
        if not legal_moves:
            return ""

        forbidden = set(extract_forbidden(observation))
        legal_filtered = [m for m in legal_moves if m not in forbidden] or legal_moves[:]
        slim = slice_board_and_moves(observation)
        prompt_context = self.prompt_pack.guidance(slim)

        # 🧠 Strategy context (important!)
        strategy_context = self.strategy.get_context()

        # 🧩 Combine everything into the LLM prompt
        final_prompt = (
            f"You are playing Stratego.\n"
            f"Strategy Context: {strategy_context}\n\n"
            f"Game State:\n{prompt_context}\n\n"
            f"Available legal moves:\n{', '.join(legal_filtered)}\n\n"
            f"Now, based on this strategy and the board, choose your next move.\n"
            f"Respond with ONLY one legal move from the list above, e.g. 'A2 B3'."
        )

        # Try several times until we get a valid move
        for _ in range(4):
            raw = self._llm_once(final_prompt)
            m = MOVE_RE.search(raw)
            if m:
                mv = m.group(0)
                if mv in legal_filtered:
                    return mv

            # fallback: stricter request
            raw2 = self._llm_once(f"Choose ONE legal move from: {', '.join(legal_filtered)}.")
            m2 = MOVE_RE.search(raw2)
            if m2:
                mv2 = m2.group(0)
                if mv2 in legal_filtered:
                    return mv2

        # fallback final
        return random.choice(legal_filtered)
