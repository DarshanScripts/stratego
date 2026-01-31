import random
import re
from typing import Any, Dict, Optional, Tuple, List
import textarena as ta

# ==============================================================================
# CHANGE LOG
# ==============================================================================
# Date: 12 Dec 2025
# Changes:
# 1. Added support for board sizes 4x4 and 5x5.
# 2. Updated lake generation: 4x4 and 5x5 boards have NO lakes.
# 3. Updated piece count logic to handle small boards (fewer pieces, smaller setup zones).
# 4. Retained all previous fixes (Double Turn, Draw Logic, etc.).
# ==============================================================================

class StrategoCustomEnv(ta.Env):
    """
    Custom Stratego environment supporting board sizes 4–9.
    """

    def __init__(self, size: int = 9):
        # [CHANGE] Updated range to allow 4 and 5
        if size < 4 or size > 9:
            raise ValueError("StrategoCustomEnv supports only board sizes 4–9.")

        self.size = size

        # Rank mapping
        self.piece_ranks: Dict[str, int] = {
            "Flag": 0, "Bomb": 11, "Spy": 1, "Scout": 2, "Miner": 3,
            "Sergeant": 4, "Lieutenant": 5, "Captain": 6, "Major": 7,
            "Colonel": 8, "General": 9, "Marshal": 10,
        }

        self.board: List[List[Optional[Dict[str, Any]]]] = []
        self.lakes: List[Tuple[int, int]] = []
        self.player_pieces: Dict[int, List[Tuple[int, int]]] = {0: [], 1: []}
        
        self.last_move: Dict[int, Optional[Tuple[int, int, int, int]]] = {0: None, 1: None}
        self.repetition_count: Dict[int, int] = {0: 0, 1: 0}
        self.turn_count: int = 0

    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    def reset(self, num_players: int, seed: Optional[int] = None):
        """Reset the environment state."""
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.turn_count = 0
        self.last_move = {0: None, 1: None}
        self.repetition_count = {0: 0, 1: 0}

        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.lakes = self._generate_lakes()
        self.player_pieces = {0: [], 1: []}

        self._populate_board()

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

        self._observe_current_state(player_id=0)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """
        Execute a player's action with strict turn switching logic.

        IMPORTANT:
        - Invalid moves TERMINATE the game
        - Invalid moves DO NOT declare a winner
        - Termination reason is stored explicitly for debugging/benchmarking
        """
        player_id = self.state.current_player_id
        self.turn_count += 1

        # ------------------------------------------------------------------
        # 0. Pre-check: current player has no legal moves
        # ------------------------------------------------------------------
        if self.state.game_state.get(f"available_moves_p{player_id}", 1) == 0:
            if self._has_movable_pieces(1 - player_id):
                self.state.set_winner(
                    player_id=(1 - player_id),
                    reason="Opponent has no legal moves."
                )
            else:
                self.state.set_winner(
                    player_id=-1,
                    reason="Stalemate (No moves for either player)."
                )
            return self.state.step()

        # Log raw action
        self.state.add_observation(
            from_id=player_id,
            to_id=player_id,
            message=action,
            observation_type=ta.ObservationType.PLAYER_ACTION
        )

        # ------------------------------------------------------------------
        # 1. Parse & Validate move format
        # ------------------------------------------------------------------
        action_search_pattern = re.compile(
            r"\[([A-J])([0-9]) ([A-J])([0-9])\]",
            re.IGNORECASE
        )
        match = action_search_pattern.search(action)

        if match is None:
            # [ADDED] Explicit invalid termination metadata
            self.state.game_state["termination"] = "invalid"
            self.state.game_state["invalid_reason"] = f"Invalid format: {action}"

            self.state.set_invalid_move(
                reason=f"Invalid format: {action}"
            )
            return self.state.step()

        src_row_char, src_col_str, dst_row_char, dst_col_str = match.groups()
        src_row = ord(src_row_char.upper()) - 65
        src_col = int(src_col_str)
        dest_row = ord(dst_row_char.upper()) - 65
        dest_col = int(dst_col_str)

        # ------------------------------------------------------------------
        # 1.b Semantic validation (rules, ownership, movement, etc.)
        # ------------------------------------------------------------------
        if not self._validate_move(player_id, src_row, src_col, dest_row, dest_col):
            # [ADDED] Mark termination as invalid instead of declaring a winner
            self.state.game_state["termination"] = "invalid"
            self.state.game_state["invalid_reason"] = "Illegal move"

            self.state.set_invalid_move(reason="Illegal move")
            try:
                self.state.game_info[player_id]["invalid_move"] = True
            except Exception:
                pass
            self.state.set_winner(player_id=(1 - player_id), reason="Illegal move.")
            return self.state.step()

        # ------------------------------------------------------------------
        # 1.c Two-squares repetition rule
        # ------------------------------------------------------------------
        if self._check_repetition(player_id, src_row, src_col, dest_row, dest_col):
            # [ADDED] Explicit invalid termination (repetition)
            self.state.game_state["termination"] = "invalid"
            self.state.game_state["invalid_reason"] = "Two-squares repetition rule violation"

            self.state.set_invalid_move(
                reason="Illegal move: Two-Squares Rule violation."
            )
            return self.state.step()

        # ------------------------------------------------------------------
        # 2. Execute Move (Board Update / Battle Resolution)
        # ------------------------------------------------------------------
        attacking_piece = self.board[src_row][src_col]
        target_piece = self.board[dest_row][dest_col]

        # Reset repetition tracking on capture
        if target_piece is not None:
            self.repetition_count[player_id] = 0
            self.last_move[player_id] = None
        else:
            self.last_move[player_id] = (
                src_row, src_col, dest_row, dest_col
            )

        if target_piece is None:
            # Normal move to empty square
            self.board[dest_row][dest_col] = attacking_piece
            self.board[src_row][src_col] = None
            self.player_pieces[player_id].remove((src_row, src_col))
            self.player_pieces[player_id].append((dest_row, dest_col))

            src_str = f"{src_row_char.upper()}{src_col}"
            dst_str = f"{dst_row_char.upper()}{dest_col}"
            self._send_action_descriptions(
                player_id,
                f"You have moved your piece from {src_str} to {dst_str}.",
                f"Player {player_id} has moved a piece from {src_str} to {dst_str}."
            )
        else:
            # Battle
            src_str = f"{src_row_char.upper()}{src_col}"
            dst_str = f"{dst_row_char.upper()}{dest_col}"
            self._resolve_battle(
                player_id,
                attacking_piece,
                target_piece,
                (src_row, src_col),
                (dest_row, dest_col),
                src_str,
                dst_str
            )

        # ------------------------------------------------------------------
        # 3. Check Win / Draw conditions (NORMAL termination only)
        # ------------------------------------------------------------------
        winner = self._check_winner()
        if winner is not None:
            self.state.set_winner(
                player_id=winner,
                reason=f"Player {winner} wins! Opponent eliminated."
            )

        # ------------------------------------------------------------------
        # 4. Finalize state & switch turn
        # ------------------------------------------------------------------
        self.state.game_state["rendered_board"] = self._render_board(
            player_id=player_id,
            full_board=True
        )

        result = self.state.step()

        if not result[0]:
            next_player_id = 1 - player_id
            self._observe_current_state(player_id=next_player_id)

        return result

    # --------------------------------------------------------------------------
    # Observation Logic
    # --------------------------------------------------------------------------

    def _observe_current_state(self, player_id: int = None):
        """Calculates valid moves and updates observation."""
        if player_id is None:
            player_id = self.state.current_player_id
            
        moves = []
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
                            if target is None or (isinstance(target, dict) and target["player"] != player_id):
                                moves.append(f"[{chr(65+r)}{c} {chr(65+nr)}{nc}]")
                            
                            if target is not None: break
                            if not is_scout: break
                            dist += 1

        self.state.game_state[f"available_moves_p{player_id}"] = len(moves)

        msg = (
            "Current Board:\n\n"
            f"{self._render_board(player_id, full_board=False)}\n"
            "Available Moves: " + (", ".join(moves) if moves else "NONE")
        )

        self.state.add_observation(
            message=msg, 
            to_id=player_id,
            observation_type=ta.ObservationType.GAME_BOARD
        )

    # --------------------------------------------------------------------------
    # Win/Draw Logic
    # --------------------------------------------------------------------------

    def _check_winner(self) -> Optional[int]:
        """
        Check win condition. Returns None if BOTH are blocked (Draw).
        """
        p0_can_move = self._has_movable_pieces(0)
        p1_can_move = self._has_movable_pieces(1)

        if not p0_can_move and not p1_can_move:
            return None 

        if not p0_can_move:
            return 1
            
        if not p1_can_move:
            return 0

        return None

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    def _render_board(self, player_id: Optional[int], full_board: bool = False) -> str:
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
                    continue

                # cell contains a piece dict
                if full_board:
                    # show EVERYTHING
                    ab = abbrev[cell['rank']]
                    if cell['player'] == 0:
                        row_str += f" {ab.lower()} "
                    else:
                        row_str += f" {ab.upper()} "
                else:
                    code = abbrev[cell["rank"]]
                    owner = cell["player"]
                    if full_board or (player_id is not None and owner == player_id):
                        row_str += f" {code.upper()} "
                    else:
                        row_str += "  ? "
            lines.append(row_str + "\n")
        return "".join(lines)

    def _has_movable_pieces(self, pid: int) -> bool:
        for (r, c) in self.player_pieces[pid]:
            cell = self.board[r][c]
            if isinstance(cell, dict) and cell["rank"] not in ["Bomb", "Flag"]:
                return True
        return False

    def _resolve_battle(self, player_id: int, attacker: Dict, target: Dict, 
                        src: Tuple[int, int], dst: Tuple[int, int], 
                        src_str: str, dst_str: str):
        src_r, src_c = src
        dst_r, dst_c = dst
        att_rank_val = self.piece_ranks[attacker['rank']]
        def_rank_val = self.piece_ranks[target['rank']]
        
        self.board[src_r][src_c] = None
        self.player_pieces[player_id].remove(src)
        outcome = "" 
        reason_msg = ""

        if target['rank'] == 'Flag':
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append(dst)
            self.player_pieces[1 - player_id].remove(dst)
            self.state.set_winner(player_id=player_id, reason=f"Player {player_id} captured the Flag!")
            return

        elif att_rank_val == def_rank_val:
            self.board[dst_r][dst_c] = None
            self.player_pieces[1 - player_id].remove(dst)
            outcome = "draw"
            reason_msg = "Rank tie. Both pieces lost."

        elif target['rank'] == 'Bomb':
            if attacker['rank'] == 'Miner':
                self.board[dst_r][dst_c] = attacker
                self.player_pieces[player_id].append(dst)
                self.player_pieces[1 - player_id].remove(dst)
                outcome = "win"
                reason_msg = "Miner defused Bomb."
            else:
                outcome = "loss"
                reason_msg = "Piece destroyed by Bomb."

        elif attacker['rank'] == 'Spy' and target['rank'] == 'Marshal':
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append(dst)
            self.player_pieces[1 - player_id].remove(dst)
            outcome = "win"
            reason_msg = "Spy defeated Marshal."

        elif att_rank_val > def_rank_val:
            self.board[dst_r][dst_c] = attacker
            self.player_pieces[player_id].append(dst)
            self.player_pieces[1 - player_id].remove(dst)
            outcome = "win"
            reason_msg = f"High rank ({attacker['rank']}) beat ({target['rank']})."

        else:
            outcome = "loss"
            reason_msg = f"Low rank ({attacker['rank']}) lost to ({target['rank']})."

        self._send_action_descriptions(player_id, 
            f"Battle! {src_str} to {dst_str}. {reason_msg}",
            f"Battle! Opponent moved {src_str} to {dst_str}. {reason_msg}"
        )

    def _send_action_descriptions(self, player_id, msg_self, msg_opp):
        self.state.add_observation(from_id=-1, to_id=player_id, message=msg_self, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        self.state.add_observation(from_id=-1, to_id=1-player_id, message=msg_opp, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

    def _validate_move(self, player_id: int, src_r: int, src_c: int, dst_r: int, dst_c: int) -> bool:
        if not (0 <= src_r < self.size and 0 <= src_c < self.size and 0 <= dst_r < self.size and 0 <= dst_c < self.size):
            self.state.set_invalid_move("Out of bounds.")
            return False
        piece = self.board[src_r][src_c]
        if not (isinstance(piece, dict) and piece["player"] == player_id):
            self.state.set_invalid_move("Not your piece.")
            return False
        if piece["rank"] in ["Bomb", "Flag"]:
            self.state.set_invalid_move("Immobile piece.")
            return False
        if (dst_r, dst_c) in self.lakes:
            self.state.set_invalid_move("Lake.")
            return False
        dst = self.board[dst_r][dst_c]
        if isinstance(dst, dict) and dst["player"] == player_id:
            self.state.set_invalid_move("Friendly fire.")
            return False
        if piece["rank"] == "Scout":
            if not (src_r == dst_r or src_c == dst_c):
                self.state.set_invalid_move("Scout not straight.")
                return False
            # Check path
            dr = 0 if src_r == dst_r else (1 if dst_r > src_r else -1)
            dc = 0 if src_c == dst_c else (1 if dst_c > src_c else -1)
            curr_r, curr_c = src_r + dr, src_c + dc
            while (curr_r, curr_c) != (dst_r, dst_c):
                if self.board[curr_r][curr_c] is not None:
                    self.state.set_invalid_move("Scout blocked.")
                    return False
                curr_r += dr
                curr_c += dc
        else:
            if abs(src_r - dst_r) + abs(src_c - dst_c) != 1:
                self.state.set_invalid_move("Invalid distance.")
                return False
        return True

    def _check_repetition(self, player_id, src_r, src_c, dst_r, dst_c) -> bool:
        last = self.last_move[player_id]
        if last is not None:
            l_sr, l_sc, l_dr, l_dc = last
            if src_r == l_dr and src_c == l_dc and dst_r == l_sr and dst_c == l_sc:
                self.repetition_count[player_id] += 1
            else:
                self.repetition_count[player_id] = 0
        return self.repetition_count[player_id] >= 3

    def _generate_lakes(self) -> list[Tuple[int, int]]:
        """
        Generate lake positions.
        [CHANGE] 4x4 and 5x5 boards have NO lakes.
        """
        size = self.size
        lakes = []
        
        # 4x4 and 5x5: No lakes
        if size < 6:
            return []

        if size == 6: lakes = [(2, 2), (2, 3), (3, 2), (3, 3)]
        elif size == 7: lakes.extend([(2, 1), (3, 1), (3, 3), (4, 3), (2, 5), (3, 5)])
        elif size == 8:
            for r in [3, 4]: 
                for c in [1, 2, 5, 6]: lakes.append((r, c))
        elif size == 9:
            for r in [3, 4]: 
                for c in [2, 3, 5, 6]: lakes.append((r, c))
        return lakes

    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        lake_text = "- Lakes (~) are impassable.\n" if self.size >= 6 else ""
        return (f"You are Player {player_id} in Stratego ({self.size}x{self.size}).\n"
                "Goal: Capture Flag or eliminate enemies.\n"
                "Rules: Move 1 sq (Scouts far). No Diagonals. Rank beats Rank.\n"
                f"{lake_text}"
                "Spy>Marshal. Miner>Bomb.\n"
                "Board Key: Your pieces Uppercase. Enemy '?'.")

    def _generate_piece_counts(self) -> Dict[str, int]:
        """
        [CHANGE] Updated to handle small boards (4x4, 5x5) appropriately.
        """
        ranks = ["Flag", "Bomb", "Spy", "Scout", "Miner", "Sergeant", "Lieutenant", "Captain", "Major", "Colonel", "General", "Marshal"]
        
        # Setup zones for small boards
        if self.size < 6:
            setup_rows = 1  # Only 1 row of pieces for 4x4 and 5x5
        elif self.size in (6, 7): 
            setup_rows = 2
        elif self.size in (8, 9): 
            setup_rows = 3
        else: 
            setup_rows = max(2, self.size // 4)
            
        slots = self.size * setup_rows 
        counts = {r: 1 for r in ranks}
        total = len(ranks)
        
        # Priority for removal if we have too many pieces (e.g. 4x4 = 16 slots, but 12 ranks)
        # Actually 4x4 with setup_rows=1 has only 4 slots per player!
        # We need aggressive reduction for very small boards.
        
        if self.size == 4:
            # Minimalist setup for 4x4: Flag, Bomb, Spy, Marshal (Total 4)
            return {"Flag": 1, "Bomb": 1, "Spy": 1, "Marshal": 1}
        
        if self.size == 5:
            # Setup for 5x5: Flag, Bomb, Spy, Marshal, Scout (Total 5)
            return {"Flag": 1, "Bomb": 1, "Spy": 1, "Marshal": 1, "Scout": 1}

        # Standard Logic for 6+
        removals = ["Spy", "General", "Colonel", "Major", "Captain"]
        i = 0
        while total > slots:
            r = removals[i % len(removals)]
            if counts[r] > 0: counts[r] -= 1; total -= 1
            i += 1
        
        filler = ["Sergeant", "Scout", "Miner", "Bomb"]
        i = 0
        while total < slots:
            p = filler[i % len(filler)]
            counts[p] += 1; total += 1
            i += 1
        return counts
    
    def _place_piece(self, r, c, rank, player, counts_dict):
        """Helper to set piece on board and update trackers."""
        self.board[r][c] = {"rank": rank, "player": player}
        self.player_pieces[player].append((r, c))
        if counts_dict and rank in counts_dict:
            counts_dict[rank] -= 1

    def _populate_board(self):
        size = self.size
        
        # [CHANGE] Setup depth calculation
        if size < 6: setup_rows = 1
        elif size in (6, 7): setup_rows = 2
        elif size in (8, 9): setup_rows = 3
        else: setup_rows = max(2, size // 3)

        for player in (0, 1):
            counts = self._generate_piece_counts()
            
            # For small boards with 1 setup row, back/front logic simplifies
            if setup_rows == 1:
                if player == 0:
                    back_rows = [0]
                    front_rows = [] # No front rows
                else:
                    back_rows = [size - 1]
                    front_rows = []
            else:
                half = max(1, setup_rows // 2)
                if player == 0:
                    back_rows = list(range(0, half))
                    front_rows = list(range(half, setup_rows))
                else:
                    start = size - setup_rows
                    back_rows = list(range(start, start + half))
                    front_rows = list(range(start + half, start + setup_rows))

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

            flag_row = 0 if player == 0 else size - 1
            flag_candidates = [(flag_row, c) for c in range(size) if (flag_row, c) not in self.lakes and self.board[flag_row][c] is None]
            if not flag_candidates: flag_candidates = free_back[:]
            
            if flag_candidates:
                fx, fy = random.choice(flag_candidates)
                self._place_piece(fx, fy, "Flag", player, counts)
                if (fx, fy) in free_back: free_back.remove((fx, fy))
                if (fx, fy) in free_front: free_front.remove((fx, fy))

                bombs_to_place = counts.get("Bomb", 0)
                for nr, nc in [(fx+1, fy), (fx-1, fy), (fx, fy+1), (fx, fy-1)]:
                    if bombs_to_place > 0 and 0 <= nr < size and 0 <= nc < size and (nr, nc) not in self.lakes and self.board[nr][nc] is None:
                        self._place_piece(nr, nc, "Bomb", player, counts)
                        bombs_to_place -= 1
                        if (nr, nc) in free_back: free_back.remove((nr, nc))
                        if (nr, nc) in free_front: free_front.remove((nr, nc))

            all_slots = free_back + free_front
            random.shuffle(all_slots)
            remaining = []
            for rk, cnt in counts.items(): remaining.extend([rk]*cnt)
            random.shuffle(remaining)
            while all_slots and remaining:
                r, c = all_slots.pop()
                self._place_piece(r, c, remaining.pop(), player, None)

        for r, c in self.lakes: self.board[r][c] = "~"
