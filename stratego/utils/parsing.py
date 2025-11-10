import re
from typing import List

MOVE_RE = re.compile(r"\[[A-J]\d\s+[A-J]\d\]")
BOARD_HEADER_RE = re.compile(r"^0\s+1\s+2\s+3\s+4\s+5\s+6\s+7\s+8\s+9$")
FORBID_LINE_RE = re.compile(r"^FORBIDDEN.*:$", re.IGNORECASE)

def extract_legal_moves(observation: str) -> List[str]:
    legal: List[str] = []
    for line in observation.splitlines():
        if line.strip().startswith("Available Moves:"):
            legal = MOVE_RE.findall(line)
    return [m.strip("[]").strip() for m in legal]  # <- normalize here

def extract_forbidden(observation: str) -> List[str]:
    forb: List[str] = []
    lines = observation.splitlines()
    for i, line in enumerate(lines):
        if FORBID_LINE_RE.match(line.strip()):
            j = i + 1
            while j < len(lines) and "[" in lines[j]:
                forb.extend(MOVE_RE.findall(lines[j]))
                j += 1
            break
    return [m.strip("[]").strip() for m in forb]  # <- normalize here


# def extract_legal_moves(observation: str) -> List[str]:
#     legal: List[str] = []
#     for line in observation.splitlines():
#         if line.strip().startswith("Available Moves:"):
#             legal = MOVE_RE.findall(line)
#     return legal

# def extract_forbidden(observation: str) -> List[str]:
#     forb: List[str] = []
#     lines = observation.splitlines()
#     for i, line in enumerate(lines):
#         if FORBID_LINE_RE.match(line.strip()):
#             j = i + 1
#             while j < len(lines) and "[" in lines[j]:
#                 forb.extend(MOVE_RE.findall(lines[j]))
#                 j += 1
#             break
#     return forb

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

def slice_board_and_moves(observation: str) -> str:
    lines = observation.splitlines()
    out: List[str] = []
    block = extract_board_block_lines(observation)
    if block:
        out.extend(block)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("Available Moves:"):
            out.append(lines[i]); break
    for i in range(len(lines) - 1, -1, -1):
        if FORBID_LINE_RE.match(lines[i].strip()):
            out.append(lines[i])
            k = i + 1
            while k < len(lines) and "[" in lines[k]:
                out.append(lines[k]); k += 1
            break
    return "\n".join(out).strip()

def strip_think(s: str) -> str:
    return re.sub(r"<think>.*?</think>", "", s, flags=re.DOTALL | re.IGNORECASE).strip()