import random
from typing import Optional
from stratego.utils.parsing import (
    extract_legal_moves,
    extract_forbidden,
    slice_board_and_moves,
    strip_think,
    MOVE_RE,
)
from stratego.prompts import PromptPack, get_prompt_pack

import textarena as ta 
from vllm import LLM, SamplingParams

try:
    from textarena.agents.basic_agents import STANDARD_GAME_PROMPT
except ImportError:
    STANDARD_GAME_PROMPT = "You are playing Stratego. You MUST respond ONLY with a valid move in the format [A0 B0]."

try:
    from textarena.agents.basic_agents import Agent
except ImportError:
    class Agent:
        def __call__(self, observation: str) -> str:
            raise NotImplementedError


class VLLMAgent(Agent):
    def __init__(self,
        llm: LLM,
        system_prompt: Optional[str] = None,
        prompt_pack: Optional[PromptPack | str] = None,
        max_new_tokens: int = 24,
        temperature: float = 0.1,
        top_p: float = 0.9
        ):
        self.llm = llm
        
        self.sampling_params = SamplingParams(
            temperature = temperature,
            top_p = top_p,
            max_tokens = max_new_tokens,
            n = 1,
            stop = ["\n"],
        )
        
        if isinstance(prompt_pack, str) or prompt_pack is None:
            self.prompt_pack: PromptPack = get_prompt_pack(prompt_pack)
        else:
            self.prompt_pack = prompt_pack

        if system_prompt is not None:
            self.system_prompt = system_prompt
        elif STANDARD_GAME_PROMPT is not None:
            self.system_prompt = STANDARD_GAME_PROMPT
        else:
            self.system_prompt = self.prompt_pack.system
            
    def _llm_once(self, content: str) -> str:
        promt = self.system_prompt + "\n" + content
        outputs = self.llm.generate([promt], self.sampling_params)
        text = (outputs[0].outputs[0].text or "").strip()
        return strip_think(text)
    
    def __call__(self, observation: str) -> str:
        legal = extract_legal_moves(observation)
        
        if not legal:
            return ""
        
        forbidden = set(extract_forbidden(observation))
        legal_filtered = [m for m in legal if m not in forbidden] or legal[:]
        
        slim = slice_board_and_moves(observation)
        guidance = self.prompt_pack.guidance(slim)
        
        for _ in range(4):
            raw = self._llm_once(guidance)
            m = MOVE_RE.search(raw)
            if m:
                mv = m.group(0)
                if mv in legal_filtered:
                    return mv
            raw2 = self._llm_once("Output exactly one legal move in the format [A0 B0]."
                "Use ONLY a move from 'Available Moves:'. No explanation."
            )
            m2 = MOVE_RE.search(raw2)
            if m2:
                mv2 = m2.group(0)
                if mv2 in legal_filtered:
                    return mv2
            
        # prompt = self.system_prompt + "\n" + guidance + observation
        # outputs = self.llm.generate([prompt], self.sampling_params)
        # text = outputs[0].outputs[0].text.strip()
        # line = text.splitlines()[0].strip()
        return random.choice(legal_filtered)