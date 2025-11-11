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
    system=(
        "You are a Stratego-playing agent.\n"
        "You MUST output exactly ONE move and NOTHING ELSE.\n"
        "The move MUST be in the format [A0 B0].\n"
        "The move MUST be one of the legal moves listed under 'Available Moves:'.\n"
    ),
    guidance_template=(
        "{board_slice}\n\n"
        "RULES:\n"
        "- Use ONLY the moves listed in 'Available Moves:'.\n"
        "- Output exactly one move in the format [A0 B0].\n"
        "- No commentary. No extra spaces or lines.\n"
        "- If multiple moves seem good, choose any ONE of them.\n"
        "\n"
        "ANSWER:\n"
    ),
)

# TODO: write down proper concise and adaptive prompt which could be implemented to the game. 
# You can refer my original base prompt from original code which I set here as BASE prompt.
# Your prompts would be exported to all codes by using __init__.py.

CONCISE = PromptPack(
    name="concise",
    system="Stratego agent. Output exactly one legal move like [SRC DST].",
    guidance_template=(
    ),
)

ADAPTIVE = PromptPack(
    name="adaptive",
    system=(
        "You are an expert Stratego agent. Consider captures, threats, and safe advancement.\n"
        "Output exactly one legal move [SRC DST]."
    ),
    guidance_template=(
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
