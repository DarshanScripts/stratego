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
    guidance_template=( "{board_slice}\n\n"
        "INSTRUCTIONS (CONCISE):\n"
        "- Pick exactly ONE move from 'Available Moves:'.\n"
        "- Never pick moves under 'FORBIDDEN'.\n"
        "- If multiple are equivalent, prefer (in order): capture > safe advance > reposition.\n"
        "- Output ONLY the move as [SRC DST] with no extra text.\n"
        "- Do not explain, justify, or comment on your choice. "
         "- Do not output anything else (no punctuation, no text, no newlines)."
        "- If no legal moves exist, output [PASS]."

    ),
)

ADAPTIVE = PromptPack(
    name="adaptive",
    system=(
        "You are an expert Stratego agent. Consider captures, threats, and safe advancement.\n"
        "Output exactly one legal move [SRC DST]."
    ),
    guidance_template=("{board_slice}\n\n"
        "INSTRUCTIONS (ADAPTIVE):\n"
        "- Choose ONE move from 'Available Moves:' only (never from 'FORBIDDEN').\n"
        "- Evaluate each candidate using these priorities (in order):\n"
        " TACTICAL GAINS: Guaranteed favorable capture (win by rank or Miner vs Bomb).\n"
        " SAFETY: Prefer moves ending on squares not capturable next turn by KNOWN/INFERRED enemy.\n"
        " MISSION ROLES: Scouts to probe/open lanes; Miners toward suspected bombs; Spy only to attack the Marshal by initiating; protect own Flag sector.\n"
        " SPACE & PRESSURE: Advance pieces that increase central control or threaten valuable targets without overexposing high ranks.\n"
        " INFORMATION: When no safe gain exists, prefer low-risk scouting over revealing high ranks.\n"
        "- Tie-breakers (apply in order):\n"
        "  Highest expected material gain this turn.\n"
        "  Lowest immediate recapture risk.\n"
        "  Improves mobility/lines (opens files, avoids lakes/choke).\n"
        "  If still tied, choose the lexicographically first [SRC DST].\n"
        "- Output ONLY the selected move in format [SRC DST]. No commentary.\n"
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
