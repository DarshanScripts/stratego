import random
import re
from typing import Any, Dict, Optional, Tuple, List

import textarena as ta

# ==============================================================================
# CHANGE LOG
# ==============================================================================
# Date: 11 Dec 2025
# Changes:
# 1. Merged initial environment structure with updated logic requirements.
# 2. Implemented specific `_generate_lakes` logic for board sizes 6x6, 7x7, 8x8, and 9x9.
# 3. Refactored `step` function to cleanly handle parsing, validation, movement, and battle resolution.
# 4. Added comprehensive docstrings and comments for all methods.
# 5. Standardized variable naming and type hinting for clarity.
# ==============================================================================

class StrategoCustomEnv(ta.Env):
    """
    Custom Stratego environment supporting board sizes 6–9.

    Features:
    - Board sizes: 6x6, 7x7, 8x8, 9x9
    - Full Stratego rules (Spy, Miner, Bomb, Flag).
    - Custom layouts based on board size.
    - Two-Squares Rule (Anti-repetition).
    - 'No-legal-moves' defeat condition.
    """

    def __init__(self, size: int = 9):
        """
        Initialize the Stratego environment.

        Args:
            size (int): The dimension of the board (6-9).
        """
        if size < 6 or size > 9:
            raise ValueError("StrategoCustomEnv supports only board sizes 6–9.")

        self.size = size

        # Rank mapping: Lower number = weaker (usually), but interactions vary (e.g. Spy, Miner)
        # Note: 0 is Flag, 11 is Bomb.
        self.piece_ranks: Dict[str, int] = {
            "Flag": 0,
            "Bomb": 11,
            "Spy": 1,
            "Scout": 2,
            "Miner": 3,
            "Sergeant": 4,
            "Lieutenant": 5,
            "Captain": 6,
            "Major": 7,
            "Colonel": 8,
            "General": 9,
            "Marshal": 10,
        }

        # Initialize core structures
        self.board: List[List[Optional[Dict[str, Any]]]] = []
        self.lakes: List[Tuple[int, int]] = []
        self.player_pieces: Dict[int, List[Tuple[int, int]]] = {0: [], 1: []}
        
        # Repetition tracking (Two-Squares Rule)
        self.last_move: Dict[int, Optional[Tuple[int, int, int, int]]] = {0: None, 1: None}
        self.repetition_count: Dict[int, int] = {0: 0, 1: 0}
        self.turn_count: int = 0

    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    # --------------------------------------------------------------------------
    # 1. Core Environment Control (Reset & Step)
    # --------------------------------------------------------------------------

    def reset(self, num_players: int, seed: Optional[int] = None):
        """
        Reset the environment state, regenerate lakes, and populate the board.

        Args:
            num_players (int): Number of players (must be 2).
            seed (Optional[int]): Random seed for reproducibility.
        """
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.turn_count = 0

        # Reset repetition tracking
        self.last_move = {0: None, 1: None}
        self.repetition_count = {0: 0, 1: 0}

        # Clear and Generate Board
        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.lakes = self._generate_lakes()
        self.player_pieces = {0: [], 1: []}

        # Place pieces
        self._populate_board()

        # Render initial state
        rendered = self._render_board(player_id=None, full_board=True)
        state_info = {
            "board": self.board,
            "player_pieces": self.player_pieces,
            "rendered_board": rendered,
        }

        self.state.reset(
            game_state=state_info,
            player_prompt_function=self._generate_player_prompt,
        )

        # Trigger first observation
        self._observe_current_state()

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """
        Execute a player's action.

        Steps:
        1. Check if player had valid moves (from previous turn calculation).
        2. Parse the action string [A0 B0].
        3. Validate the move (rules, bounds, lakes).
        4. Check Two-Squares repetition rule.
        5. Execute move (Move to empty or Battle).
        6. Generate observations for both players.
        7. Check Win Conditions.
        """
        player_id = self.state.current_player_id
        self.turn_count += 1

        # --- 0. Pre-check: Did the player have legal moves? ---
        # If available_moves is 0 (set in previous observation), they lose immediately.
        if self.state.game_state.get(f"available_moves_p{player_id}", 1) == 0:
            if self._has_movable_pieces(1 - player_id):
                self.state.set_winner(player_id=(1 - player_id), reason="Opponent has no legal moves.")
            else:
                self.state.set_winner(player_id=-1, reason="Stalemate (No moves for either player).")
            return self.state.step()

        # Log action
        self.state.add_observation(
            from_id=player_id, to_id=player_id, 
            message=action, observation_type=ta.ObservationType.PLAYER_ACTION
        )

        # --- 1. Parse Action ---
        action_search_pattern = re.compile(r"\[([A-J])([0-9]) ([A-J])([0-9])\]", re.IGNORECASE)
        match = action_search_pattern.search(action)

        if match is None:
            reason = f"Invalid action format. Expected [A0 B0], got {action}."
            self.state.set_invalid_move(reason=reason)
            return self.state.step()

        src_row_char, src_col_str, dst_row_char, dst_col_str = match.groups()
        src_row = ord(src_row_char.upper()) - 65
        src_col = int(src_col_str)
        dest_row = ord(dst_row_char.upper()) - 65
        dest_col = int(dst_col_str)
        
        source_str = f"{src_row_char.upper()}{src_col}"
        dest_str = f"{dst_row_char.upper()}{dest_col}"

        # --- 2. Validate Move ---
        if not self._validate_move(player_id, src_row, src_col, dest_row, dest_col):
            # The _validate_move method sets the invalid_move reason in state
            return self.state.step()

        # --- 3. Check Repetition (Two-Squares Rule) ---
        if self._check_repetition(player_id, src_row, src_col, dest_row, dest_col):
            self.state.set_invalid_move(reason="Illegal move: Two-Squares Rule violation (repetition).")
            return self.state.step()

        # --- 4. Execution ---
        attacking_piece = self.board[src_row][src_col]
        target_piece = self.board[dest_row][dest_col]

        # Reset repetition count if a battle occurs or a piece is captured (irreversible change)
        # Otherwise, update the last move tracker
        if target_piece is not None:
             self.repetition_count[player_id] = 0
             self.last_move[player_id] = None
        else:
             self.last_move[player_id] = (src_row, src_col, dest_row, dest_col)

        # A. Move to Empty Square
        if target_piece is None:
            self.board[dest_row][dest_col] = attacking_piece
            self.board[src_row][src_col] = None
            self.player_pieces[player_id].remove((src_row, src_col))
            self.player_pieces[player_id].append((dest_row, dest_col))

            # Descriptions
            msg_self = f"You have moved your piece from {source_str} to {dest_str}."
            msg_opp = f"Player {player_id} has moved a piece from {source_str} to {dest_str}."
            self._send_action_descriptions(player_id, msg_self, msg_opp)

        # B. Battle
        else:
            self._resolve_battle(player_id, attacking_piece, target_piece, 
                                 (src_row, src_col), (dest_row, dest_col), 
                                 source_str, dest_str)

        # --- 5. Game Over Check ---
        winner = self._check_winner()
        if winner is not None:
            self.state.set_winner(player_id=winner, reason=f"Player {winner} wins! Opponent has no movable pieces or Flag captured.")
        elif self.turn_count > 1000:
            self.state.set_winner(player_id=-1, reason="Turn limit reached.")

        # --- 6. Finalize Step ---
        # Update render
        self.state.game_state["rendered_board"] = self._render_board(player_id=player_id, full_board=True)
        
        result = self.state.step()
        
        # If game continues, calculate legal moves for the NEXT player
        if not result[0]: # if not done
            self._observe_current_state()
            
        return result

    # --------------------------------------------------------------------------
    # 2. Battle & Move Helpers
    # --------------------------------------------------------------------------

    def _resolve_battle(self, player_id: int, attacker: Dict, target: Dict, 
                        src: Tuple[int, int], dst: Tuple[int, int], 
                        src_str: str, dst_str: str):
        """
        Handle the logic when one piece attacks another.
        """
        src_r, src_c = src
        dst_r, dst_c = dst
        
        att_rank_val = self.piece_ranks[attacker['rank']]
        def_rank_val = self.piece_ranks[target['rank']]
        att_rank_name = attacker['rank']
        def_rank_name = target['rank']

        # Remove attacker from source regardless of outcome
        self.board[src_r][src_c] = None
        self.player_pieces[player_id].remove(src)

        outcome = "" # "win", "loss", "draw"

        # 1. Capture Flag
        if def_rank_name == 'Flag':
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append(dst)
            self.player_pieces[1 - player_id].remove(dst)
            self.state.set_winner(player_id=player_id, reason=[f"Player {player_id} captured the Flag!"])
            return # Immediate end

        # 2. Equal Ranks (Both die)
        elif att_rank_val == def_rank_val:
            self.board[dst_r][dst_c] = None
            self.player_pieces[1 - player_id].remove(dst)
            outcome = "draw"
            reason_msg = "As the ranks are the same, both pieces lost."

        # 3. Bomb Interactions
        elif def_rank_name == 'Bomb':
            if att_rank_name == 'Miner':
                # Miner defuses Bomb
                self.board[dst_r][dst_c] = attacker
                self.player_pieces[player_id].append(dst)
                self.player_pieces[1 - player_id].remove(dst)
                outcome = "win"
                reason_msg = "As miners can defuse bombs, you won the battle."
            else:
                # Attacker dies
                outcome = "loss"
                reason_msg = "As the attacker is not a miner, you lost the battle."

        # 4. Spy vs Marshal
        elif att_rank_name == 'Spy' and def_rank_name == 'Marshal':
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append(dst)
            self.player_pieces[1 - player_id].remove(dst)
            outcome = "win"
            reason_msg = "As the attacker is a spy and the destination is a marshal, you won the battle."

        # 5. Standard Rank Comparison
        elif att_rank_val > def_rank_val:
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append(dst)
            self.player_pieces[1 - player_id].remove(dst)
            outcome = "win"
            reason_msg = "As the attacker is a higher rank than the destination, you won the battle."

        else: # Attacker < Defender
            outcome = "loss"
            reason_msg = "As the attacker is a lower rank than the destination, you lost the battle."

        # Send Observations
        self._construct_battle_messages(player_id, src_str, dst_str, att_rank_name, def_rank_name, outcome, reason_msg)

    def _construct_battle_messages(self, player_id: int, src: str, dst: str, 
                                   att_rank: str, def_rank: str, outcome: str, reason: str):
        """Helper to format and send battle observation messages."""
        
        # Base templates
        p1_base = f"You have moved your piece from {src} to {dst}. The attacking piece was {att_rank} and the destination piece was {def_rank}."
        p2_base = f"Player {player_id} has moved a piece from {src} to {dst}. The attacking piece was {att_rank} and the destination piece was {def_rank}."

        # Construct specific messages based on outcome
        if outcome == "draw":
            msg_self = f"{p1_base} {reason}"
            msg_opp = f"{p2_base} {reason}"
        elif outcome == "win":
            msg_self = f"{p1_base} {reason}"
            # For opponent, if p1 won, p2 lost
            opp_reason = reason.replace("you won", "you lost").replace("you lost", "you won") # simple flip
            msg_opp = f"{p2_base} {opp_reason}"
        else: # loss
            msg_self = f"{p1_base} {reason}"
            opp_reason = reason.replace("you won", "you lost").replace("you lost", "you won")
            msg_opp = f"{p2_base} {opp_reason}"

        self._send_action_descriptions(player_id, msg_self, msg_opp)

    def _send_action_descriptions(self, player_id, msg_self, msg_opp):
        self.state.add_observation(from_id=-1, to_id=player_id, message=msg_self, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        self.state.add_observation(from_id=-1, to_id=1-player_id, message=msg_opp, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

    def _check_repetition(self, player_id, src_r, src_c, dst_r, dst_c) -> bool:
        """
        Updates repetition counters and returns True if move is illegal due to Two-Squares Rule.
        """
        last = self.last_move[player_id]
        if last is not None:
            l_sr, l_sc, l_dr, l_dc = last
            # Check if this move is the exact reverse of the last move
            if src_r == l_dr and src_c == l_dc and dst_r == l_sr and dst_c == l_sc:
                self.repetition_count[player_id] += 1
            else:
                self.repetition_count[player_id] = 0
        
        return self.repetition_count[player_id] >= 3

    # --------------------------------------------------------------------------
    # 3. Board Generation & Validation
    # --------------------------------------------------------------------------

    def _generate_lakes(self) -> List[Tuple[int, int]]:
        """
        Generate lake positions depending on board size.
        Updated: 11 Dec 2025

        - 6×6 → one 2×2 lake block in center
        - 7×7 → two pairs on sides + center pair
        - 8×8, 9×9 → two 2×2 blocks (left and right) with space between
        """
        size = self.size
        lakes = []

        # --- Board 6x6: Center 2×2 block ---
        if size == 6:
            lakes = [
                (2, 2), (2, 3),
                (3, 2), (3, 3)
            ]

        # --- Board 7x7: Two side pairs + center pair ---
        elif size == 7:
            # Left pair: column 1
            lakes.extend([(2, 1), (3, 1)])
            # Center pair: column 3
            lakes.extend([(3, 3), (4, 3)])
            # Right pair: column 5
            lakes.extend([(2, 5), (3, 5)])

        # --- Board 8x8: Two 2×2 blocks (left and right) with gap ---
        elif size == 8:
            # Left 2×2 block: rows 3-4, cols 1-2
            for r in [3, 4]:
                for c in [1, 2]:
                    lakes.append((r, c))
            
            # Right 2×2 block: rows 3-4, cols 5-6
            for r in [3, 4]:
                for c in [5, 6]:
                    lakes.append((r, c))

        # --- Board 9x9: Two 2×2 blocks (left and right) with gap ---
        elif size == 9:
            # Left 2×2 block: rows 3-4, cols 2-3
            for r in [3, 4]:
                for c in [2, 3]:
                    lakes.append((r, c))
            
            # Right 2×2 block: rows 3-4, cols 5-6
            for r in [3, 4]:
                for c in [5, 6]:
                    lakes.append((r, c))

        return lakes

    def _generate_piece_counts(self) -> Dict[str, int]:
        """
        Determine how many pieces of each rank exist based on board size.
        Ensures at least 1 of each rank, then fills remaining slots.
        """
        ranks = [
            "Flag", "Bomb", "Spy", "Scout", "Miner",
            "Sergeant", "Lieutenant", "Captain", "Major",
            "Colonel", "General", "Marshal",
        ]

        # Calculate setup area size
        if self.size in (6, 7):
            setup_rows = 2
        elif self.size in (8, 9):
            setup_rows = 3
        else:
            setup_rows = max(2, self.size // 4)

        slots = self.size * setup_rows 
        counts = {r: 1 for r in ranks}
        total = len(ranks)

        # 1. Reduce pieces if board is too small for 1 of each (unlikely for sizes >6)
        removal_priority = ["Spy", "General", "Colonel", "Major", "Captain"]
        i = 0
        while total > slots:
            r = removal_priority[i % len(removal_priority)]
            if counts[r] > 0:
                counts[r] -= 1
                total -= 1
            i += 1

        # 2. Fill extra slots
        filler = ["Sergeant", "Scout", "Miner", "Bomb"]
        i = 0
        while total < slots:
            p = filler[i % len(filler)]
            counts[p] += 1
            total += 1
            i += 1

        return counts

    def _populate_board(self):
        """
        Randomly populate the board for both players respecting setup zones.
        Ensures Flags are protected and Bombs are placed strategically.
        """
        size = self.size
        # Determine setup depth
        if size in (6, 7): setup_rows = 2
        elif size in (8, 9): setup_rows = 3
        else: setup_rows = max(2, size // 3)

        for player in (0, 1):
            counts = self._generate_piece_counts()
            
            # Define Setup Zones (Back vs Front of setup area)
            half = max(1, setup_rows // 2)
            if player == 0:
                back_rows = list(range(0, half))
                front_rows = list(range(half, setup_rows))
            else:
                start = size - setup_rows
                back_rows = list(range(start, start + half))
                front_rows = list(range(start + half, start + setup_rows))

            # Helper to get valid empty spots
            def get_free_spots(rows):
                spots = []
                for r in rows:
                    for c in range(size):
                        if (r, c) not in self.lakes and self.board[r][c] is None:
                            spots.append((r, c))
                random.shuffle(spots)
                return spots

            free_back = get_free_spots(back_rows)
            free_front = get_free_spots(front_rows)

            # --- A. Place Flag ---
            # Try to place on the very back row
            flag_row = 0 if player == 0 else size - 1
            flag_candidates = [
                (flag_row, c) for c in range(size) 
                if (flag_row, c) not in self.lakes and self.board[flag_row][c] is None
            ]
            if not flag_candidates: flag_candidates = free_back[:]
            
            fx, fy = random.choice(flag_candidates)
            self._place_piece(fx, fy, "Flag", player, counts)
            # Remove used spot from free lists
            if (fx, fy) in free_back: free_back.remove((fx, fy))
            if (fx, fy) in free_front: free_front.remove((fx, fy))

            # --- B. Place Bombs around Flag ---
            bombs_to_place = counts.get("Bomb", 0)
            neighbors = [(fx+1, fy), (fx-1, fy), (fx, fy+1), (fx, fy-1)]
            for nr, nc in neighbors:
                if bombs_to_place > 0 and 0 <= nr < size and 0 <= nc < size:
                    if (nr, nc) not in self.lakes and self.board[nr][nc] is None:
                        self._place_piece(nr, nc, "Bomb", player, counts)
                        bombs_to_place -= 1
                        if (nr, nc) in free_back: free_back.remove((nr, nc))
                        if (nr, nc) in free_front: free_front.remove((nr, nc))

            # --- C. Place remaining pieces ---
            all_slots = free_back + free_front
            random.shuffle(all_slots)

            # Create list of remaining pieces
            remaining_pieces = []
            for rank, count in counts.items():
                remaining_pieces.extend([rank] * count)
            random.shuffle(remaining_pieces)

            # Fill board
            while all_slots and remaining_pieces:
                r, c = all_slots.pop()
                rank = remaining_pieces.pop()
                self._place_piece(r, c, rank, player, None) # Counts already decremented or list built

        # Mark lakes
        for r, c in self.lakes:
            self.board[r][c] = "~"

    def _place_piece(self, r, c, rank, player, counts_dict):
        """Helper to set piece on board and update trackers."""
        self.board[r][c] = {"rank": rank, "player": player}
        self.player_pieces[player].append((r, c))
        if counts_dict and rank in counts_dict:
            counts_dict[rank] -= 1

    def _validate_move(self, player_id: int, src_r: int, src_c: int, dst_r: int, dst_c: int) -> bool:
        """Check standard Stratego movement rules."""
        size = self.size

        # Bounds
        if not (0 <= src_r < size and 0 <= src_c < size and 0 <= dst_r < size and 0 <= dst_c < size):
            self.state.set_invalid_move("Coordinates out of bounds.")
            return False

        piece = self.board[src_r][src_c]
        if not (isinstance(piece, dict) and piece["player"] == player_id):
            self.state.set_invalid_move("You must move one of your own pieces.")
            return False

        rank = piece["rank"].lower()
        if rank in ["bomb", "flag"]:
            self.state.set_invalid_move("Bombs and Flags cannot move.")
            return False

        if (dst_r, dst_c) in self.lakes:
            self.state.set_invalid_move("Cannot move into a lake.")
            return False

        dst_piece = self.board[dst_r][dst_c]
        if isinstance(dst_piece, dict) and dst_piece["player"] == player_id:
            self.state.set_invalid_move("Cannot move onto your own piece.")
            return False

        # Scout (Move any distance straight)
        if rank == "scout":
            if not (src_r == dst_r or src_c == dst_c):
                self.state.set_invalid_move("Scouts must move in a straight line.")
                return False
            
            # Check for blocking pieces
            dr = 0 if src_r == dst_r else (1 if dst_r > src_r else -1)
            dc = 0 if src_c == dst_c else (1 if dst_c > src_c else -1)
            
            curr_r, curr_c = src_r + dr, src_c + dc
            while (curr_r, curr_c) != (dst_r, dst_c):
                if self.board[curr_r][curr_c] is not None: # Lake or Piece
                    self.state.set_invalid_move("Scout path is blocked.")
                    return False
                curr_r += dr
                curr_c += dc
        else:
            # Normal pieces (1 step)
            if abs(src_r - dst_r) + abs(src_c - dst_c) != 1:
                self.state.set_invalid_move("Non-scout pieces must move exactly one square orthogonally.")
                return False

        return True

    # --------------------------------------------------------------------------
    # 4. Observation & Helper Methods
    # --------------------------------------------------------------------------

    def _observe_current_state(self):
        """Calculates valid moves and updates the observation for the current player."""
        player_id = self.state.current_player_id
        moves = []
        
        # Simple scan to generate legal moves for the prompt
        # (This duplicates some logic from _validate_move but is needed for the AI prompt)
        for r in range(self.size):
            for c in range(self.size):
                piece = self.board[r][c]
                if isinstance(piece, dict) and piece["player"] == player_id:
                    if piece["rank"] in ["Bomb", "Flag"]: continue
                    
                    is_scout = (piece["rank"] == "Scout")
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        dist = 1
                        while True:
                            nr, nc = r + dr*dist, c + dc*dist
                            if not (0 <= nr < self.size and 0 <= nc < self.size): break
                            if (nr, nc) in self.lakes: break
                            
                            target = self.board[nr][nc]
                            # If empty or enemy -> Valid move
                            if target is None or (isinstance(target, dict) and target["player"] != player_id):
                                moves.append(f"[{chr(65+r)}{c} {chr(65+nr)}{nc}]")
                            
                            # Logic to stop or continue
                            if target is not None: break # Blocked by piece (enemy or friend)
                            if not is_scout: break # Non-scouts stop after 1 step
                            dist += 1

        # Store count for "No Moves" loss condition
        self.state.game_state[f"available_moves_p{player_id}"] = len(moves)

        msg = (
            "Current Board:\n\n"
            f"{self._render_board(player_id, full_board=False)}\n"
            "Available Moves: " + (", ".join(moves) if moves else "NONE")
        )

        self.state.add_observation(message=msg, observation_type=ta.ObservationType.GAME_BOARD)

    def _render_board(self, player_id: Optional[int], full_board: bool = False) -> str:
        """ASCII Render of the board."""
        abbrev = {
            "Flag": "FL", "Bomb": "BM", "Spy": "SP", "Scout": "SC",
            "Miner": "MN", "Sergeant": "SG", "Lieutenant": "LT",
            "Captain": "CP", "Major": "MJ", "Colonel": "CL",
            "General": "GN", "Marshal": "MS",
        }
        lines = ["   " + " ".join(f"{i:>3}" for i in range(self.size)) + "\n"]
        for r in range(self.size):
            row_str = f"{chr(65+r):<3}"
            for c in range(self.size):
                if (r, c) in self.lakes:
                    row_str += "  ~ "
                    continue
                
                cell = self.board[r][c]
                if cell is None:
                    row_str += "  . "
                else:
                    code = abbrev[cell["rank"]]
                    owner = cell["player"]
                    # Show piece if it belongs to player, or if full_board (spectator/end game) is requested
                    if full_board or (player_id is not None and owner == player_id):
                        row_str += f" {code.upper()} "
                    else:
                        row_str += "  ? "
            lines.append(row_str + "\n")
        return "".join(lines)

    def _has_movable_pieces(self, pid: int) -> bool:
        """Check if a player has any piece that is not a Bomb or Flag."""
        for (r, c) in self.player_pieces[pid]:
            cell = self.board[r][c]
            if isinstance(cell, dict) and cell["rank"] not in ["Bomb", "Flag"]:
                return True
        return False

    #Condition when a player has no movable pieces then its a draw
    def _check_winner(self) -> Optional[int]:
        """
        Check win condition based on movable pieces.
        Correctly handles the case where BOTH players have no movable pieces (Draw).
        """
        p0_can_move = self._has_movable_pieces(0)
        p1_can_move = self._has_movable_pieces(1)

        # Case 1: Both blocked -> Returns None here, so step() can trigger the Stalemate/Draw logic
        if not p0_can_move and not p1_can_move:
            return None 

        # Case 2: Only P0 blocked -> P1 wins
        if not p0_can_move:
            return 1
            
        # Case 3: Only P1 blocked -> P0 wins
        if not p1_can_move:
            return 0

        return None

    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        """Generate the system prompt for the AI."""
        return (
            f"You are Player {player_id} in Stratego (custom board size {self.size}x{self.size}).\n"
            "Goal: Capture the enemy Flag or eliminate all movable enemy pieces.\n\n"
            "Rules:\n"
            "- Move one piece per turn [Source Destination] (e.g., [C2 C3]).\n"
            "- Scouts move any distance straight. Others move 1 square.\n"
            "- Bombs/Flags cannot move.\n"
            "- Miner defeats Bomb. Spy defeats Marshal (if attacking).\n"
            "- Two-Squares Rule: No repeated back-and-forth moves (>3 times).\n"
            "- Lakes (~) are impassable.\n\n"
            "Board Key: Your pieces are Uppercase. Enemy is '?'."
        )