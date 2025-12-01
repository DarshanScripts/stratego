"""Move Processor: Utilities for parsing and analyzing moves.

Handles:
- Move parsing from LLM output
- Piece extraction from board
- Board state serialization
- Move direction computation
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class MoveDetails:
    """Parsed move information for logging."""
    src_pos: str = ""
    dst_pos: str = ""
    piece_type: str = ""
    target_piece: str = ""  # Piece at destination (if any)
    move_direction: str = ""  # N/S/E/W
    board_state: str = ""  # Serialized board state
    available_moves: str = ""  # List of valid moves


def parse_move(action: str) -> Tuple[str, str]:
    """
    Extract source and destination positions from move string.
    
    Args:
        action: Move string like "[D4 E4]"
        
    Returns:
        Tuple of (src_pos, dst_pos) or ("", "") if parsing fails
    """
    move_pattern = r'\[([A-J]\d+)\s+([A-J]\d+)\]'
    match = re.search(move_pattern, action)
    if match:
        return match.group(1), match.group(2)
    return "", ""


def get_piece_at_position(board: List[List], position: str) -> str:
    """
    Get piece type at a board position.
    
    Args:
        board: 10x10 game board
        position: Position string like "D4"
        
    Returns:
        piece_type or "" if not found
    """
    if not position:
        return ""
    
    try:
        row = ord(position[0]) - ord('A')
        col = int(position[1:])
        piece = board[row][col]
        
        if piece and isinstance(piece, dict) and 'rank' in piece:
            return piece['rank']
    except (IndexError, ValueError, TypeError):
        pass
    
    return ""


def compute_move_direction(src_pos: str, dst_pos: str) -> str:
    """
    Compute move direction from source to destination.
    
    Args:
        src_pos: Source position like "D4"
        dst_pos: Destination position like "E4"
        
    Returns:
        Direction: "N", "S", "E", "W", or "" if invalid
    """
    if not src_pos or not dst_pos:
        return ""
    try:
        src_row = ord(src_pos[0]) - ord('A')
        dst_row = ord(dst_pos[0]) - ord('A')
        src_col = int(src_pos[1:])
        dst_col = int(dst_pos[1:])
        
        if dst_row < src_row:
            return "N"  # Moving up (toward A)
        elif dst_row > src_row:
            return "S"  # Moving down (toward J)
        elif dst_col > src_col:
            return "E"  # Moving right
        elif dst_col < src_col:
            return "W"  # Moving left
    except (IndexError, ValueError):
        pass
    return ""


def serialize_board(board: List[List], player_id: int = 0) -> str:
    """
    Serialize board state to a compact string for training.
    Format: Each cell as "RC:PIECE" where R=row, C=col, PIECE=short rank or ?/~/.
    
    Args:
        board: 10x10 game board
        player_id: Current player (to show their pieces, hide opponent's)
        
    Returns:
        Compact board string representation
    """
    # Short forms matching the game board display (to store it in csv and datasets)
    RANK_SHORT = {
        "Flag": "FL",
        "Spy": "SP",
        "Scout": "SC",
        "Miner": "MN",
        "Sergeant": "SG",
        "Lieutenant": "LT",
        "Captain": "CP",
        "Major": "MJ",
        "Colonel": "CL",
        "General": "GN",
        "Marshal": "MS",
        "Bomb": "BM",
    }
    
    if not board:
        return ""
    
    cells = []
    row_labels = "ABCDEFGHIJ"
    
    for r, row in enumerate(board):
        for c, cell in enumerate(row):
            pos = f"{row_labels[r]}{c}"
            if cell is None:
                cells.append(f"{pos}:.")
            elif cell == "~":
                cells.append(f"{pos}:~")
            elif isinstance(cell, dict):
                rank = cell.get('rank', '?')
                owner = cell.get('player', -1)
                if owner == player_id:
                    # Show own piece rank (use short form)
                    short_rank = RANK_SHORT.get(rank, rank)
                    cells.append(f"{pos}:{short_rank}")
                else:
                    # Hide opponent's piece
                    cells.append(f"{pos}:?")
            else:
                cells.append(f"{pos}:{cell}")
    
    return "|".join(cells)


def extract_available_moves(observation: str) -> str:
    """
    Extract available moves from observation string.
    
    Args:
        observation: Full observation text from environment
        
    Returns:
        Comma-separated list of available moves
    """
    # Pattern: "Available Moves: [D1 E1], [D5 E5], ..."
    match = re.search(r'Available Moves:\s*(.+?)(?:\n|$)', observation)
    if match:
        moves_str = match.group(1).strip()
        # Extract just the moves like "[D1 E1]"
        moves = re.findall(r'\[[A-J]\d+\s+[A-J]\d+\]', moves_str)
        return ",".join(moves)
    return ""


def process_move(action: str, board: List[List], observation: str = "", player_id: int = 0) -> MoveDetails:
    """
    Process a move and extract all relevant details for logging.
    
    Args:
        action: Move string from LLM
        board: Current game board
        observation: Full observation text (for available moves)
        player_id: Current player ID
        
    Returns:
        MoveDetails dataclass with all extracted info
    """
    src_pos, dst_pos = parse_move(action)
    piece_type = get_piece_at_position(board, src_pos)
    target_piece = get_piece_at_position(board, dst_pos)
    move_direction = compute_move_direction(src_pos, dst_pos)
    board_state = serialize_board(board, player_id)
    available_moves = extract_available_moves(observation)
    
    return MoveDetails(
        src_pos=src_pos,
        dst_pos=dst_pos,
        piece_type=piece_type,
        target_piece=target_piece,
        move_direction=move_direction,
        board_state=board_state,
        available_moves=available_moves
    )
