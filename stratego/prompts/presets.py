
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class PromptPack:
    name: str
    system: str
    guidance_template: str

    def guidance(self, board_slice: str) -> str:
        return self.guidance_template.format(board_slice=board_slice)

BASE = PromptPack(
    name="base",
    # This is what original STANDARD_GAME_PROMPT from main code was.
    system=(
        "You are a competitive Stratego-playing agent.\n"
        "Strictly follow the rules. Output exactly ONE legal move in the format [SRC DST] "
        "and nothing else."
    ),
    # This is guidance prompt from main code.
    guidance_template=(
        "{board_slice}\n\n"
        "INSTRUCTIONS:\n"
        "- Choose exactly ONE move that appears in 'Available Moves:' above.\n"
        "- Do NOT choose any move listed under FORBIDDEN (if present).\n"
        "- Output ONLY the move in format [A0 B0]. No other text.\n"
    ),
)

# TODO: write down proper concise and adaptive prompt which could be implemented to the game. 
# You can refer my original base prompt from original code which I set here as BASE prompt.
# Your prompts would be exported to all codes by using __init__.py.

CONCISE = PromptPack(
    name="concise",
    system="Stratego agent. Output exactly one legal move like [SRC DST].",
    guidance_template=(
        "{board_slice}\n\n"
        "INSTRUCTIONS:\n"
        "- Choose exactly ONE move from the 'Available Moves:' section above.\n"
        "- Do NOT choose any move listed under 'FORBIDDEN' (if present).\n"
        "- Prefer captures that are likely to win, or otherwise prefer safe advancement.\n"
        "- Avoid exposing high-value pieces to obvious captures.\n"
        "- Output ONLY the move in format [A0 B0] and nothing else.\n"
    ),
)


ADAPTIVE = PromptPack(
    name="adaptive",
    system=(
        "You are an expert Stratego agent. Consider captures, threats, and safe advancement.\n"
        "Output exactly one legal move [SRC DST]."
    ),
    guidance_template=(
        "{board_slice}\n\n"
        "GUIDANCE (ADAPTIVE):\n"
        "- Consider immediate captures first: prefer trades that win material or remove high-value opponents.\n"
        "- Assess risk: avoid moves that expose your high-rank pieces to probable capture.\n"
        "- Prioritize safe advancement and creating or denying threats when captures are unclear.\n"
        "- Respect 'FORBIDDEN' moves (do not choose them) and choose only from 'Available Moves:'.\n"
        "- If multiple moves are comparable, prefer those that increase mobility or secure key squares.\n"
        "- Output ONLY the chosen move in format [A0 B0] and nothing else.\n"
    ),
)

_REGISTRY: Dict[str, PromptPack] = {
    BASE.name: BASE,
    CONCISE.name: CONCISE,
    ADAPTIVE.name: ADAPTIVE,
}

def get_prompt_pack(name: str | None) -> PromptPack:
    if not name:
        return BASE
    key = name.lower()
    if key not in _REGISTRY:
        return BASE
    return _REGISTRY[key]
