"""
Move Processor: Utilities for parsing and analyzing moves.

Handles:
- Move parsing from LLM output
- Piece extraction from board
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


def process_move(action: str, board: List[List]) -> MoveDetails:
    """
    Process a move and extract all relevant details for logging.
    
    Args:
        action: Move string from LLM
        board: Current game board
        
    Returns:
        MoveDetails dataclass with all extracted info
    """
    src_pos, dst_pos = parse_move(action)
    piece_type = get_piece_at_position(board, src_pos)
    
    return MoveDetails(
        src_pos=src_pos,
        dst_pos=dst_pos,
        piece_type=piece_type
    )
