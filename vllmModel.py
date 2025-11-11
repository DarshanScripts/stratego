from typing import Optional
from stratego.utils.parsing import slice_board_and_moves, strip_think
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

from stratego.prompts import PromptPack, get_prompt_pack

class VLLMAgent(Agent):
    def __init__(self, llm: LLM, max_new_tokens: int = 64, prompt_pack: Optional[PromptPack | str] = None):
        self.llm = llm
        self.sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.9,
            max_tokens=max_new_tokens,
        )
        if isinstance(prompt_pack, str) or prompt_pack is None:
            self.prompt_pack: PromptPack = get_prompt_pack(prompt_pack)
        else:
            self.prompt_pack = prompt_pack

        self.system_prompt = STANDARD_GAME_PROMPT if STANDARD_GAME_PROMPT is not None else self.prompt_pack.system
    
    def __call__(self, observation: str) -> str:
        slim = slice_board_and_moves(observation)
        guidance = self.prompt_pack.guidance(slim)
        prompt = self.system_prompt + "\n" + guidance + observation
        outputs = self.llm.generate([prompt], self.sampling_params)
        text = outputs[0].outputs[0].text.strip()
        line = text.splitlines()[0].strip()
        return line