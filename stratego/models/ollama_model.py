import os, random
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

import requests
import json

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
        legal = extract_legal_moves(observation)
        if not legal:
            return ""
 
        forbidden = set(extract_forbidden(observation))
        legal_filtered = [m for m in legal if m not in forbidden] or legal[:]
        slim = slice_board_and_moves(observation)
        base_guidance = self.prompt_pack.guidance(slim)
        
        # Build move history section for prompt
        history_text = ""
        if self.move_history:
            history_text = "\n\nYOUR RECENT MOVES:\n"
            for entry in self.move_history[-5:]:  # Last 5 moves
                history_text += f"   • {entry['text']}\n"
            
            # Check for immediate repeat
            if len(self.move_history) >= 1:
                last_move = self.move_history[-1]["move"]
                history_text += f"\nDO NOT repeat your last move: {last_move}\n"
            
            # Check for alternating pattern (A-B-A)
            if len(self.move_history) >= 3:
                moves = [m["move"] for m in self.move_history[-3:]]
                if moves[0] == moves[2]:
                    history_text += f"AVOID alternating pattern: {moves[0]} ↔ {moves[1]}\n"
            
            history_text += "\nChoose a DIFFERENT move that advances your strategy.\n"
        
        guidance = base_guidance + history_text

        # Get moves to avoid (recent history)
        recent_moves = set()
        if len(self.move_history) >= 2:
            recent_moves = {m["move"] for m in self.move_history[-2:]}
        
        for attempt in range(4):
            raw = self._llm_once(guidance)
            m = MOVE_RE.search(raw)
            if m:
                mv = m.group(0)
                
                # Check if it's a repeat of recent move
                if mv in recent_moves and len(recent_moves) > 0:
                    # Filter out recent moves from legal options
                    non_repeat_moves = [lm for lm in legal_filtered if lm not in recent_moves]
                    if non_repeat_moves:
                        print(f"   LLM proposed recent move {mv}, trying alternatives...")
                        legal_filtered = non_repeat_moves
                        continue
                
                if mv in legal_filtered:
                    return mv

            raw2 = self._llm_once("Output exactly one legal move [A0 B0].")
            m2 = MOVE_RE.search(raw2)
            if m2:
                mv2 = m2.group(0)
                if mv2 in legal_filtered:
                    return mv2

        return random.choice(legal_filtered)