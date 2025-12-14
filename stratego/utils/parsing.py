import re
from typing import Any, List, Sequence

MOVE_RE = re.compile(r"\[[A-J]\d\s+[A-J]\d\]")
# Allow leading spaces so 6x6 duel headers like "     0   1   2   3   4   5" are captured
BOARD_HEADER_RE = re.compile(r"^\s*0(\s+\d+)+$")
FORBID_LINE_RE = re.compile(r"^FORBIDDEN.*:$", re.IGNORECASE)

def _obs_to_str(observation: Any) -> str:

    if isinstance(observation, str):
        return observation

    if isinstance(observation, Sequence):
        parts: List[str] = []
        for item in observation:
            # (from_id, message, obs_type)
            if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], str):
                parts.append(item[1])
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return str(observation)

def extract_legal_moves(observation: Any) -> List[str]:
    text = _obs_to_str(observation)
    legal: List[str] = []
    for line in text.splitlines():
        if line.strip().startswith("Available Moves:"):
            legal = MOVE_RE.findall(line)
    return legal

def extract_forbidden(observation: Any) -> List[str]:
    text = _obs_to_str(observation)
    forb: List[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if FORBID_LINE_RE.match(line.strip()):
            j = i + 1
            while j < len(lines) and "[" in lines[j]:
                forb.extend(MOVE_RE.findall(lines[j]))
                j += 1
            break
    return forb

def extract_board_block_lines(observation: str, size: int = 10) -> List[str]:
    text = _obs_to_str(observation)
    lines = text.splitlines()
    header_idx = None
    detected_size = size

    for i in range(len(lines) - 1, -1, -1):
        if BOARD_HEADER_RE.match(lines[i].strip()):
            header_idx = i
            # Auto-detect board size from header numbers (e.g., "0 1 2 3 4 5" -> size 6)
            try:
                nums = [int(n) for n in lines[i].split() if n.isdigit()]
                if nums:
                    detected_size = max(nums) + 1
            except Exception:
                pass
            break
    if header_idx is None or header_idx + detected_size >= len(lines):
        return []
    return lines[header_idx: header_idx + detected_size + 1]

def slice_board_and_moves(observation: Any, size: int = 10) -> str:
    text = _obs_to_str(observation)
    lines = text.splitlines()
    out: List[str] = []

    block = extract_board_block_lines(text, size)
    if block:
        out.extend(block)

    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("Available Moves:"):
            out.append(lines[i])
            break

    for i in range(len(lines) - 1, -1, -1):
        if FORBID_LINE_RE.match(lines[i].strip()):
            out.append(lines[i])
            k = i + 1
            while k < len(lines) and "[" in lines[k]:
                out.append(lines[k])
                k += 1
            break

    return "\n".join(out).strip()

def strip_think(s: str) -> str:
    return re.sub(r"<think>.*?</think>", "", s, flags=re.DOTALL | re.IGNORECASE).strip()
