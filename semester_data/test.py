from typing import List
from stratego.prompts.presets import get_prompt_pack
import textarena as ta 
from vllm import LLM
from vllmModel import VLLMAgent
import re

BOARD_HEADER_RE = re.compile(r"^0\s+1\s+2\s+3\s+4\s+5\s+6\s+7\s+8\s+9$")

def extract_board_block_lines(observation: str) -> List[str]:
    lines = observation.splitlines()
    header_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if BOARD_HEADER_RE.match(lines[i].strip()):
            header_idx = i
            break
    if header_idx is None or header_idx + 10 >= len(lines):
        return []
    return lines[header_idx: header_idx + 11]

def print_board(observation: str):
    block = extract_board_block_lines(observation)
    if block:
        print("\n".join(block))

llm1 = LLM(model="openai/gpt-oss-20b",
    trust_remote_code=True,
    dtype="bfloat16",
    tensor_parallel_size=1,
    gpu_memory_utilization=0.32
    )

llm2 = LLM(model="Qwen/Qwen3-0.6B",
    trust_remote_code=True,
    dtype="bfloat16",
    tensor_parallel_size=1,
    gpu_memory_utilization=0.18
    )

agents = {
    0: VLLMAgent(llm1, prompt_pack=get_prompt_pack("base")),
    1: VLLMAgent(llm2, prompt_pack=get_prompt_pack("base"))
}

# initialize the environment
env = ta.make(env_id="Stratego-v0")
env.reset(num_players=len(agents))

# main game loop
done = False 
while not done:
  player_id, observation = env.get_observation()
  print_board(observation)
  action = agents[player_id](observation)
  done, step_info = env.step(action=action)
  print(action)
rewards, game_info = env.close()
print(rewards)
print(game_info)