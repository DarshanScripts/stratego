import re, random
from typing import Optional, Dict, Tuple, List, Any
import textarena as ta

class StrategoDuelEnv(ta.Env):
    """ A two-player implementation of the board game Stratego on a 6x6 board """
    def __init__(self):
        """ Initialize the environment for a 6x6 board size. """
        self.piece_counts = {
            'Flag': 1, 'Bomb': 2, 'Spy': 1, 'Scout': 1, 'Miner': 1,
            'General': 1, 'Marshal': 1
        }
        self.piece_ranks = {
            'Flag': 0, 'Bomb': 11, 'Spy': 1, 'Scout': 2, 'Miner': 3,
            'General': 9, 'Marshal': 10
        }
        # Lakes at center: (2,2), (2,3), (3,2), (3,3)
        self.lakes = [(2, 2), (2, 3), (3, 2), (3, 3)]
        self.player_pieces = {0: [], 1: []}
        self.board = [[None for _ in range(6)] for _ in range(6)]
        self.turn_count = 0
        
        # --- REPETITION TRACKING (Two-Square Rule) ---
        # Stores the last move as (start_row, start_col, end_row, end_col)
        self.last_move = {0: None, 1: None} 
        # Counts consecutive repetitions
        self.repetition_count = {0: 0, 1: 0}

    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    def reset(self, num_players: int, seed: Optional[int]=None):
        """ Reset the environment to start a new game """
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.turn_count = 0
        
        # Reset Repetition logic
        self.last_move = {0: None, 1: None}
        self.repetition_count = {0: 0, 1: 0}
        
        self.board = self._populate_board()
        
        # Render board (God Mode / Full Board enabled for visibility)
        rendered_board = self._render_board(player_id=None, full_board=True)
        
        game_state={
            "board": self.board, 
            "player_pieces": self.player_pieces, 
            "rendered_board": rendered_board
        }
        
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        self._observe_current_state()
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        """ Generates the player prompt. """
        prompt = (
            f"You are Player {player_id} in Stratego Duel (6x6).\n"
            "Goal: Capture the Flag or eliminate opponent pieces.\n"
            "### RULES\n"
            "1. **Board:** 6x6 Grid (A-F, 0-5). Lakes (~) are blocked.\n"
            "2. **Move:** [Source Destination] e.g., `[A0 B0]`.\n"
            "3. **Attack:** Move onto opponent. Higher rank wins.\n"
            "4. **Two-Squares Rule:** You cannot move a piece back and forth between the same two squares more than 3 consecutive times.\n"
            "\n"
            "Here is the board:\n"
        )
        return prompt

    def _observe_current_state(self):
        """ Observe state. Adds BACKTICKS for parser compatibility. """
        BOARD_SIZE = 6 
        player_id = self.state.current_player_id
        available_moves = []

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if isinstance(piece, dict) and piece['player'] == player_id:
                    if piece['rank'].lower() in ['bomb', 'flag']: continue
                    is_scout = piece['rank'].lower() == 'scout'
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if is_scout:
                            distance = 1
                            while True:
                                new_row, new_col = row + (dr * distance), col + (dc * distance)
                                if not (0 <= new_row < 6 and 0 <= new_col < 6): break
                                if (new_row, new_col) in self.lakes: break 
                                target = self.board[new_row][new_col]
                                if target is None or target == "~":
                                    if target is None:
                                        available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                        distance += 1
                                    else: break
                                elif isinstance(target, dict) and target['player'] != player_id:
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                    break
                                else: break
                        else:
                            new_row, new_col = row + dr, col + dc
                            if 0 <= new_row < 6 and 0 <= new_col < 6:
                                if (new_row, new_col) in self.lakes: continue
                                target = self.board[new_row][new_col]
                                if (target is None or (isinstance(target, dict) and target['player'] != player_id)):
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")

        self.state.game_state[f'available_moves_p{player_id}'] = len(available_moves)

        obs_msg = (
            f"Current Board:\n"
            f"```\n"
            f"{self._render_board(player_id=player_id, full_board=False)}"
            f"```\n"
            f"Available Moves: {', '.join(available_moves)}"
        )

        self.state.add_observation(
            message=obs_msg,
            observation_type=ta.ObservationType.GAME_BOARD
        )
    
    def _populate_board(self):
        for player in range(2):
            rows = range(0, 2) if player == 0 else range(4, 6)
            while True:
                r, c = random.choice(rows), random.randint(0, 5)
                if (r, c) not in self.lakes and self.board[r][c] is None:
                    self.board[r][c] = {'rank': 'Flag', 'player': player}
                    self.player_pieces[player].append((r, c))
                    flag_pos = (r, c)
                    break
            
            bombs = self.piece_counts['Bomb']
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]: 
                br, bc = flag_pos[0]+dr, flag_pos[1]+dc
                if bombs > 0 and 0<=br<6 and 0<=bc<6 and self.board[br][bc] is None and (br,bc) not in self.lakes and br in rows:
                    self.board[br][bc] = {'rank': 'Bomb', 'player': player}
                    self.player_pieces[player].append((br, bc))
                    bombs -= 1
            
            all_pieces = []
            for p, c in self.piece_counts.items():
                if p != 'Flag': all_pieces.extend([p] * (c if p != 'Bomb' else bombs))
            
            for rank in all_pieces:
                while True:
                    r, c = random.choice(rows), random.randint(0, 5)
                    if self.board[r][c] is None and (r, c) not in self.lakes:
                        self.board[r][c] = {'rank': rank, 'player': player}
                        self.player_pieces[player].append((r, c))
                        break
        
        for r, c in self.lakes: self.board[r][c] = "~"
        return self.board

    def _render_board(self, player_id, full_board: bool = False):
        """ 
        Renders the 6x6 board using the same spacing logic as the 10x10 version.
        Ensures Headers (0, 1, 2) align with Cells ( . , FL, BM).
        """
        BOARD_SIZE = 6
        abbr = {'Flag':'FL','Bomb':'BM','Spy':'SP','Scout':'SC','Miner':'MN','General':'GN','Marshal':'MS'}
        
        res = []
        # Header Alignment: 3 spaces + center-aligned number in 3-char block + space
        column_headers = "   " + " ".join([f"{i:>3}" for i in range(BOARD_SIZE)])
        res.append(column_headers + "\n")
        
        for r in range(BOARD_SIZE):
            row_label = chr(r + 65)
            # Row Label Alignment: Fixed width 3
            row_render = [f"{row_label:<3}"] 
            
            for c in range(BOARD_SIZE):
                if (r, c) in self.lakes: cell = "  ~ "
                elif self.board[r][c] is None: cell = "  . "
                else:
                    p = self.board[r][c]
                    if p == "~": cell = "  ~ "
                    else:
                        code = abbr.get(p['rank'], "??")
                        if full_board: 
                            cell = f" {code.lower() if p['player']==0 else code.upper()} "
                        elif p['player'] == player_id: 
                            cell = f" {code.upper()} "
                        else: 
                            cell = "  ? "
                
                row_render.append(cell)
            res.append("".join(row_render) + "\n")
        return "".join(res)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        self.turn_count += 1
        pid = self.state.current_player_id
        
        if self.state.game_state.get(f'available_moves_p{pid}', 1) == 0:
            winner = 1-pid if self._has_movable_pieces(1-pid) else -1
            self.state.set_winner(player_id=winner, reason="No moves/Stalemate")
            return self.state.step()

        self.state.add_observation(from_id=pid, to_id=pid, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        
        match = re.search(r"\[([A-F])([0-5]) ([A-F])([0-5])\]", action, re.IGNORECASE)
        if not match:
            self.state.set_invalid_move(reason=f"Invalid format '{action}'. Use [A0 B0].")
        else:
            sr, sc = ord(match.group(1).upper())-65, int(match.group(2))
            dr, dc = ord(match.group(3).upper())-65, int(match.group(4))
            
            if self._validate_move(pid, sr, sc, dr, dc):
                
                # --- REPETITION CHECK START ---
                is_repetition = False
                last = self.last_move[pid]
                
                # Check if move is reverse of last move (A->B, then B->A)
                if last is not None:
                    last_sr, last_sc, last_dr, last_dc = last
                    if sr == last_dr and sc == last_dc and dr == last_sr and dc == last_sc:
                        is_repetition = True
                
                if is_repetition:
                    self.repetition_count[pid] += 1
                else:
                    self.repetition_count[pid] = 0 # Reset if new path taken
                
                self.last_move[pid] = (sr, sc, dr, dc)

                if self.repetition_count[pid] >= 3:
                    self.state.set_invalid_move(reason="Illegal Repetition: Cannot move back and forth >3 times.")
                    return self.state.step()
                # --- REPETITION CHECK END ---

                att, tgt = self.board[sr][sc], self.board[dr][dc]
                
                if tgt is None:
                    self.board[dr][dc], self.board[sr][sc] = att, None
                    self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc))
                    self.state.add_observation(from_id=-1, to_id=pid, message="Move success.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    self.state.add_observation(from_id=-1, to_id=1-pid, message="Opponent moved.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                else:
                    # Attack breaks repetition chain
                    self.repetition_count[pid] = 0
                    self.last_move[pid] = None

                    ar, tr = self.piece_ranks[att['rank']], self.piece_ranks[tgt['rank']]
                    if ar == tr: 
                        self.board[sr][sc] = self.board[dr][dc] = None
                        self.player_pieces[pid].remove((sr, sc)); self.player_pieces[1-pid].remove((dr, dc))
                    elif tgt['rank'] == 'Bomb': 
                        if att['rank'] == 'Miner': 
                            self.board[dr][dc], self.board[sr][sc] = att, None
                            self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc)); self.player_pieces[1-pid].remove((dr, dc))
                        else: 
                            self.board[sr][sc] = None; self.player_pieces[pid].remove((sr, sc))
                    elif tgt['rank'] == 'Flag': 
                        self.state.set_winner(player_id=pid, reason="Flag Captured!"); return self.state.step()
                    elif att['rank'] == 'Spy' and tgt['rank'] == 'Marshal': 
                        self.board[dr][dc], self.board[sr][sc] = att, None
                        self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc)); self.player_pieces[1-pid].remove((dr, dc))
                    elif ar > tr: 
                        self.board[dr][dc], self.board[sr][sc] = att, None
                        self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc)); self.player_pieces[1-pid].remove((dr, dc))
                    else: 
                        self.board[sr][sc] = None; self.player_pieces[pid].remove((sr, sc))
                    
                    msg = "Battle occurred."
                    self.state.add_observation(from_id=-1, to_id=pid, message=msg, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    self.state.add_observation(from_id=-1, to_id=1-pid, message=msg, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

        w = self._check_winner()
        if w is not None: self.state.set_winner(player_id=w, reason="Elimination.")
        elif self._check_stalemate(): self.state.set_winner(player_id=-1, reason="Stalemate.")
        elif self.turn_count > 1000: self.state.set_winner(player_id=-1, reason="Turn limit.")
        
        self.state.game_state["rendered_board"] = self._render_board(player_id=pid, full_board=True)
        res = self.state.step()
        if not res[0]: self._observe_current_state()
        return res

    def _validate_move(self, pid, sr, sc, dr, dc):
        if not (0<=sr<6 and 0<=sc<6 and 0<=dr<6 and 0<=dc<6): return False
        if self.board[sr][sc] is None or self.board[sr][sc]['player'] != pid: return False
        if (dr, dc) in self.lakes: return False
        if self.board[dr][dc] and self.board[dr][dc] != "~" and self.board[dr][dc]['player'] == pid: return False
        if self.board[sr][sc]['rank'] in ['Bomb', 'Flag']: return False
        if self.board[sr][sc]['rank'] == 'Scout':
            if sr != dr and sc != dc: return False
            return True 
        if abs(sr-dr) + abs(sc-dc) != 1: return False
        return True

    def _check_winner(self):
        for p in range(2):
            if not any([self.board[r][c] and self.board[r][c]!="~" and self.board[r][c]['rank'] not in ['Bomb','Flag'] for r,c in self.player_pieces[p]]):
                return 1-p
        return None

    def _has_movable_pieces(self, pid):
        return any([self.board[r][c] and self.board[r][c]!="~" and self.board[r][c]['rank'] not in ['Bomb','Flag'] for r,c in self.player_pieces[pid]])

    def _check_stalemate(self):
        return not self._has_movable_pieces(0) and not self._has_movable_pieces(1)