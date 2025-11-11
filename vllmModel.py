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
    def __init__(self, llm: LLM, max_new_tokens: int = 64):
        self.llm = llm
        self.sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.9,
            max_tokens=max_new_tokens,
        )

    def __call__(self, observation: str) -> str:
        prompt = STANDARD_GAME_PROMPT + "\n" + observation
        outputs = self.llm.generate([prompt], self.sampling_params)
        text = outputs[0].outputs[0].text.strip()
        line = text.splitlines()[0].strip()
        return line