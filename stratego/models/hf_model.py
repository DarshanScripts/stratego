import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from .base import AgentLike
from ..utils.parsing import extract_legal_moves, extract_forbidden, slice_board_and_moves, MOVE_RE
from ..prompts import get_prompt_pack

class HFLocalAgent(AgentLike):
  def __init__(self, model_id: str, prompt_pack: str="base", **gen):
    self.model_name = f"hf:{model_id}"
    self.pack = get_prompt_pack(prompt_pack)
    self.tok = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    self.model = AutoModelForCausalLM.from_pretrained(
      model_id, torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
      device_map="auto"
    )
    self.gen = dict(max_new_tokens=32, do_sample=True, temperature=0.1, top_p=0.9, **gen)

  def __call__(self, observation: str) -> str:
    legal = extract_legal_moves(observation)
    if not legal: return ""
    forb = set(extract_forbidden(observation))
    legal_filtered = [m for m in legal if m not in forb] or legal

    sys = self.pack.system
    user = self.pack.guidance(slice_board_and_moves(observation))
    prompt = f"{sys}\n\n{user}"

    inputs = self.tok(prompt, return_tensors="pt").to(self.model.device)
    with torch.no_grad():
      out = self.model.generate(**inputs, **self.gen)
    text = self.tok.decode(out[0], skip_special_tokens=True)
    m = MOVE_RE.search(text[len(prompt):])
    return m.group(0) if m and m.group(0) in legal_filtered else legal_filtered[0]
