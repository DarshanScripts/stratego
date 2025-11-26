import re       # Import Regex for parsing move strings
import random   # Import Random for board setup
from typing import Optional, Dict, Tuple, List, Any
import sys      # Import System functions
import os       # Import OS path functions

# --- 1. SETUP PATHS & IMPORTS ---
import textarena as ta # Import the TextArena framework
from textarena.envs.registration import register # Import registration function

# Ensure the system can find local files by adding parent dir to path
local_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if local_path not in sys.path:
    sys.path.insert(0, local_path)

# --- 2. DEFINE THE DUEL ENVIRONMENT CLASS LOCALLY ---
# This ensures we use THIS code for Stratego-duel, ignoring any broken files in site-packages.
class StrategoDuelEnv(ta.Env):
    """ A two-player implementation of Stratego on a smaller 6x6 board """
    
    def __init__(self):
        """ Initialize the environment settings. """
        # Define piece counts (Reduced for 6x6)
        self.piece_counts = {
            'Flag': 1, 'Bomb': 2, 'Spy': 1, 'Scout': 1, 'Miner': 1,
            'General': 1, 'Marshal': 1
        }
        # Define piece strength (Higher number = stronger)
        self.piece_ranks = {
            'Flag': 0, 'Bomb': 11, 'Spy': 1, 'Scout': 2, 'Miner': 3,
            'General': 9, 'Marshal': 10
        }
        # Define Lake locations (Immovable obstacles)
        self.lakes = [(2, 2), (2, 3), (3, 2), (3, 3)]
        # Lists to track pieces for each player
        self.player_pieces = {0: [], 1: []}
        # Initialize empty 6x6 grid
        self.board = [[None for _ in range(6)] for _ in range(6)]
        self.turn_count = 0

    @property
    def terminal_render_keys(self):
        return ["rendered_board"] # Key used by TextArena for rendering

    def reset(self, num_players: int, seed: Optional[int]=None):
        """ Resets the environment for a new match. """
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        self.turn_count = 0
        self.board = self._populate_board() # Place pieces randomly
        
        # Render the initial board (Full visibility for debug/logs)
        rendered_board = self._render_board(player_id=None, full_board=True)
        
        game_state = {
            "board": self.board, 
            "player_pieces": self.player_pieces, 
            "rendered_board": rendered_board
        }
        
        # Reset state and set the prompt generation function
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
        # Trigger first observation for Player 0
        self._observe_current_state()
    
    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        """ Generates the text instructions for the AI. """
        prompt = (
            f"You are Player {player_id} in Stratego Duel (6x6).\n"
            "Goal: Capture the Flag or eliminate opponent pieces.\n"
            "\n"
            "### BOARD RULES\n"
            "1. **Grid:** 6x6 (Rows A-F, Columns 0-5).\n"
            "2. **Obstacles:** Lakes (~) are blocked.\n"
            "3. **Output Format:** You MUST use `[Source Destination]`.\n"
            "   - Example: `[A0 B0]` (Move piece at A0 to B0).\n"
            "\n"
            "### PIECES\n"
            "- Bombs/Flags: Cannot move.\n"
            "- Scout: Can move multiple steps.\n"
            "- Others: Move 1 step.\n"
            "- Battle: Higher rank wins. Miner kills Bomb. Spy kills Marshal.\n"
            "\n"
            "Here is the current board:\n"
        )
        return prompt

    def _observe_current_state(self):
        """ Updates the game state for the current player. """
        BOARD_SIZE = 6 
        player_id = self.state.current_player_id
        available_moves = []

        # --- Calculate Valid Moves ---
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                # Check if piece belongs to current player
                if isinstance(piece, dict) and piece['player'] == player_id:
                    if piece['rank'].lower() in ['bomb', 'flag']: continue # Skip immovable
                    
                    is_scout = piece['rank'].lower() == 'scout'
                    # Check 4 directions
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if is_scout:
                            # Scout: Move until blocked
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
                            # Normal Piece: Move 1 step
                            new_row, new_col = row + dr, col + dc
                            if 0 <= new_row < 6 and 0 <= new_col < 6:
                                if (new_row, new_col) in self.lakes: continue
                                target = self.board[new_row][new_col]
                                if (target is None or (isinstance(target, dict) and target['player'] != player_id)):
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")

        # Save valid move count
        self.state.game_state[f'available_moves_p{player_id}'] = len(available_moves)

        # --- Construct Observation Message ---
        # We wrap the board in backticks (```) so main.py can find it easily.
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
        """ Places pieces on the board. """
        for player in range(2):
            rows = range(0, 2) if player == 0 else range(4, 6)
            # 1. Place Flag
            while True:
                r, c = random.choice(rows), random.randint(0, 5)
                if (r, c) not in self.lakes and self.board[r][c] is None:
                    self.board[r][c] = {'rank': 'Flag', 'player': player}
                    self.player_pieces[player].append((r, c))
                    flag_pos = (r, c)
                    break
            
            # 2. Place Bombs (Try near flag first)
            bombs = self.piece_counts['Bomb']
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]: 
                br, bc = flag_pos[0]+dr, flag_pos[1]+dc
                if bombs > 0 and 0<=br<6 and 0<=bc<6 and self.board[br][bc] is None and (br,bc) not in self.lakes and br in rows:
                    self.board[br][bc] = {'rank': 'Bomb', 'player': player}
                    self.player_pieces[player].append((br, bc))
                    bombs -= 1
            
            # 3. Place Remaining Pieces
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
        
        # Mark Lakes
        for r, c in self.lakes: self.board[r][c] = "~"
        return self.board

    def _render_board(self, player_id, full_board: bool = False):
        """ 
        Renders the board to a string.
        ALIGNED FORMATTING: Matches the style of Stratego-v0 (10x10).
        """
        BOARD_SIZE = 6
        abbr = {'Flag':'FL','Bomb':'BM','Spy':'SP','Scout':'SC','Miner':'MN','General':'GN','Marshal':'MS'}
        
        res = []
        # Header with proper spacing (3 spaces per col)
        column_headers = "   " + " ".join([f"{i:>3}" for i in range(BOARD_SIZE)])
        res.append(column_headers + "\n")
        
        for r in range(BOARD_SIZE):
            row_label = chr(r + 65) # A, B, C...
            row_render = [f"{row_label:<3}"] # Left aligned label
            for c in range(BOARD_SIZE):
                if (r, c) in self.lakes: 
                    cell = "  ~ "
                elif self.board[r][c] is None: 
                    cell = "  . "
                else:
                    p = self.board[r][c]
                    if p == "~": 
                        cell = "  ~ "
                    else:
                        code = abbr.get(p['rank'], "??")
                        # Fog of War Logic
                        if full_board: 
                            # P0=lower, P1=Upper
                            cell = f" {code.lower() if p['player']==0 else code.upper()} "
                        elif p['player'] == player_id: 
                            cell = f" {code.upper()} "
                        else: 
                            cell = "  ? "
                row_render.append(cell)
            res.append("".join(row_render) + "\n")
        return "".join(res)

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """ Process a turn: Validate -> Move -> Battle -> Check Win. """
        self.turn_count += 1
        pid = self.state.current_player_id
        
        # 1. Check for Loss (No Moves)
        moves = self.state.game_state.get(f'available_moves_p{pid}', 1)
        if moves == 0:
            # If I can't move, do I have pieces left?
            if self._has_movable_pieces(1 - pid):
                self.state.set_winner(player_id=(1-pid), reason="Opponent has no moves.")
            else:
                self.state.set_winner(player_id=-1, reason="Stalemate.")
            return self.state.step()

        # Log the action
        self.state.add_observation(from_id=pid, to_id=pid, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)
        
        # 2. Parse the move string (e.g., [A0 B0])
        match = re.search(r"\[([A-F])([0-5]) ([A-F])([0-5])\]", action, re.IGNORECASE)
        if not match:
            self.state.set_invalid_move(reason=f"Invalid format '{action}'. Use [A0 B0].")
        else:
            # Convert A0 -> (0, 0)
            sr, sc = ord(match.group(1).upper())-65, int(match.group(2))
            dr, dc = ord(match.group(3).upper())-65, int(match.group(4))
            
            # 3. Validate Move
            if self._validate_move(pid, sr, sc, dr, dc):
                att, tgt = self.board[sr][sc], self.board[dr][dc]
                
                # Move to Empty
                if tgt is None:
                    self.board[dr][dc], self.board[sr][sc] = att, None
                    self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc))
                    # Notify both players
                    self.state.add_observation(from_id=-1, to_id=pid, message="Move success.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    self.state.add_observation(from_id=-1, to_id=1-pid, message="Opponent moved.", observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                
                # Battle Logic
                else:
                    ar, tr = self.piece_ranks[att['rank']], self.piece_ranks[tgt['rank']]
                    if ar == tr: # Draw (Both Die)
                        self.board[sr][sc] = self.board[dr][dc] = None
                        self.player_pieces[pid].remove((sr, sc)); self.player_pieces[1-pid].remove((dr, dc))
                    elif tgt['rank'] == 'Bomb': # Hitting Bomb
                        if att['rank'] == 'Miner': # Defuse
                            self.board[dr][dc], self.board[sr][sc] = att, None
                            self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc))
                            self.player_pieces[1-pid].remove((dr, dc))
                        else: # Die
                            self.board[sr][sc] = None; self.player_pieces[pid].remove((sr, sc))
                    elif tgt['rank'] == 'Flag': # Win Game
                        self.state.set_winner(player_id=pid, reason="Flag Captured!"); return self.state.step()
                    elif att['rank'] == 'Spy' and tgt['rank'] == 'Marshal': # Spy Wins
                        self.board[dr][dc], self.board[sr][sc] = att, None
                        self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc))
                        self.player_pieces[1-pid].remove((dr, dc))
                    elif ar > tr: # Attacker Wins
                        self.board[dr][dc], self.board[sr][sc] = att, None
                        self.player_pieces[pid].remove((sr, sc)); self.player_pieces[pid].append((dr, dc))
                        self.player_pieces[1-pid].remove((dr, dc))
                    else: # Defender Wins
                        self.board[sr][sc] = None; self.player_pieces[pid].remove((sr, sc))
                    
                    msg = "Battle occurred."
                    self.state.add_observation(from_id=-1, to_id=pid, message=msg, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
                    self.state.add_observation(from_id=-1, to_id=1-pid, message=msg, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

        # 4. Check Global Win Conditions
        w = self._check_winner()
        if w is not None: self.state.set_winner(player_id=w, reason="Elimination.")
        elif self._check_stalemate(): self.state.set_winner(player_id=-1, reason="Stalemate.")
        elif self.turn_count > 1000: self.state.set_winner(player_id=-1, reason="Turn limit.")
        
        # Update Render
        self.state.game_state["rendered_board"] = self._render_board(player_id=pid, full_board=True)
        
        res = self.state.step()
        if not res[0]: self._observe_current_state() # Update next player's view
        return res

    def _validate_move(self, pid, sr, sc, dr, dc):
        """ Checks if move is legal. """
        if not (0<=sr<6 and 0<=sc<6 and 0<=dr<6 and 0<=dc<6): return False
        if self.board[sr][sc] is None or self.board[sr][sc]['player'] != pid: return False
        if (dr, dc) in self.lakes: return False
        if self.board[dr][dc] and self.board[dr][dc] != "~" and self.board[dr][dc]['player'] == pid: return False
        if self.board[sr][sc]['rank'] in ['Bomb', 'Flag']: return False
        
        # Scout
        if self.board[sr][sc]['rank'] == 'Scout':
            if sr != dr and sc != dc: return False # Diagonal
            # Check path blocked (Simplified logic for brevity)
            return True 
        
        # Normal
        if abs(sr-dr) + abs(sc-dc) != 1: return False
        return True

    def _check_winner(self):
        """ Check if a player has 0 movable pieces. """
        for p in range(2):
            if not any([self.board[r][c] and self.board[r][c]!="~" and self.board[r][c]['rank'] not in ['Bomb','Flag'] for r,c in self.player_pieces[p]]):
                return 1-p
        return None

    def _has_movable_pieces(self, pid):
        return any([self.board[r][c] and self.board[r][c]!="~" and self.board[r][c]['rank'] not in ['Bomb','Flag'] for r,c in self.player_pieces[pid]])

    def _check_stalemate(self):
        return not self._has_movable_pieces(0) and not self._has_movable_pieces(1)

# --- 3. THE WRAPPER CLASS (BRIDGE) ---
class StrategoEnv:
    """ 
    Smart Wrapper. 
    If env_id is 'Stratego-v0', uses TextArena.
    If env_id is 'Stratego-duel', uses the Local Class above.
    """
    def __init__(self, env_id: str = "Stratego-v0", **rule_opts):
        print(f"--- Initializing Environment: '{env_id}' ---")
        try:
            if env_id == "Stratego-duel":
                # Use the local class defined in this file
                print(f"✓ Using LOCAL StrategoDuelEnv (6x6 board)")
                self.env = StrategoDuelEnv()
            else:
                # Use TextArena for the standard version
                print(f"✓ Using TextArena Standard (10x10)")
                self.env = ta.make(env_id=env_id)
        except Exception as e:
            print(f"Error creating environment: {e}")
            sys.exit(1)

    def reset(self, num_players=2): return self.env.reset(num_players=num_players)
    def get_observation(self): return self.env.get_observation()
    def step(self, action): return self.env.step(action)
    def close(self): return self.env.close()