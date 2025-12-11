import random
import re
from typing import Any, Dict, Optional, Tuple
import textarena as ta


class StrategoCustomEnv(ta.Env):
    """
    A size-configurable Stratego environment that extends the original TextArena implementation.
    It overrides only what depends on board size and initial setup, while keeping all battle
    and rules logic exactly as in the original engine.
    """

    def __init__(self, size: int = 10):
        self.size = size            # store board dimension
        # super().__init__()          # calls original StrategoEnv constructor

        # Replace the default 10×10 board with custom size
        self.board = [[None for _ in range(size)] for _ in range(size)]

        # Generate lakes suitable for the given board size
        self.lakes = self._generate_lakes()

        # Scale piece counts to size
        self.piece_counts = self._generate_piece_counts()
        
        self.piece_ranks = {
            'Flag': 0, 'Bomb': 11, 'Spy': 1, 'Scout': 2, 'Miner': 3,
            'Sergeant': 4, 'Lieutenant': 5, 'Captain': 6, 'Major': 7,
            'Colonel': 8, 'General': 9, 'Marshal': 10
        }

        # Reinitialize containers
        self.player_pieces = {0: [], 1: []}

    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    # -------------------------------------------------------------------------
    # 1) LAKES
    # -------------------------------------------------------------------------
    def _generate_lakes(self):
        """Small boards: one lake in the center. Large boards: a 2×2 lake block."""
        mid = self.size // 2

        if self.size >= 8:
            return [
                (mid - 1, mid - 1), (mid - 1, mid),
                (mid,     mid - 1), (mid,     mid)
            ]
        else:
            return [(mid, mid)]

    # -------------------------------------------------------------------------
    # 2) PIECE COUNTS
    # -------------------------------------------------------------------------
    def _generate_piece_counts(self):
        """Ensure ≥1 of each rank, then scale to board size."""
        ranks = [
            'Flag', 'Bomb', 'Spy', 'Scout', 'Miner',
            'Sergeant', 'Lieutenant', 'Captain', 'Major',
            'Colonel', 'General', 'Marshal'
        ]

        counts = {r: 1 for r in ranks}   # minimum one of each

        target = (self.size * self.size) // 4
        current = len(ranks)

        filler = ['Scout', 'Miner', 'Sergeant', 'Bomb']
        i = 0
        while current < target:
            p = filler[i % len(filler)]
            counts[p] += 1
            current += 1
            i += 1

        return counts

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """ Execute an action in the environment """
        player_id = self.state.current_player_id

        ## update the observation
        self.state.add_observation(from_id=player_id, to_id=player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

        ## action search pattern
        action_search_pattern = re.compile(r"\[([A-J])([0-9]) ([A-J])([0-9])\]", re.IGNORECASE)
        match = action_search_pattern.search(action)

        if match is None:
            reason=f"Invalid action format. Player {player_id} did not input a move in the format [A0 B0]."
            self.state.set_invalid_move(reason=reason)
            try:
                self.state.game_info[player_id]["invalid_move"] = True
            except Exception:
                pass
            self.state.set_winner(player_id=(1 - player_id), reason=reason)
            return self.state.step()

        else:
            src_row, src_col, dest_row, dest_col = match.groups()
            src_row, dest_row = src_row.upper(), dest_row.upper()
            source = f"{src_row}{src_col}"
            dest = f"{dest_row}{dest_col}"
            src_row, src_col = ord(src_row) - 65, int(src_col)
            dest_row, dest_col = ord(dest_row) - 65, int(dest_col)
             

            ## check if the source and destination are valid
            if self._validate_move(player_id=player_id, src_r=src_row, src_c=src_col, dst_r=dest_row, dst_c=dest_col):

                attacking_piece = self.board[src_row][src_col]
                target_piece = self.board[dest_row][dest_col]

                if target_piece is None:
                    ## move to an empty square
                    self.board[dest_row][dest_col] = attacking_piece
                    self.board[src_row][src_col] = None
                    self.player_pieces[player_id].remove((src_row, src_col))
                    self.player_pieces[player_id].append((dest_row, dest_col))
                    
                    ## add the observation to both players separately
                    message=f"You have moved your piece from {source} to {dest}."
                    self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    message=f"Player {player_id} has moved a piece from {source} to {dest}."
                    self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                else:
                    ## battle
                    attacking_rank = self.piece_ranks[attacking_piece['rank']]
                    target_rank = self.piece_ranks[target_piece['rank']]
                    if attacking_rank == target_rank:
                        ## both pieces are removed
                        self.board[src_row][src_col] = None
                        self.board[dest_row][dest_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))

                        ## add the observation to both players separately
                        message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the ranks are the same, both pieces lost."
                        self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the ranks are the same, both pieces lost."
                        self.state.add_observation(from_id=-1, to_id=1 - player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    elif target_piece['rank'] == 'Bomb':
                        if attacking_piece['rank'] == 'Miner':
                            ## Miner defuses the bomb
                            self.board[dest_row][dest_col] = attacking_piece
                            self.board[src_row][src_col] = None
                            self.player_pieces[player_id].remove((src_row, src_col))
                            self.player_pieces[player_id].append((dest_row, dest_col))

                            ## add the observation to both players separately
                            message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As miners can defuse bombs, you won the battle."
                            self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                            message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As miners can defuse bombs, you lost the battle."
                            self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        else:
                            ## attacking piece is destroyed
                            self.board[src_row][src_col] = None
                            self.player_pieces[player_id].remove((src_row, src_col))

                            ## add the observation to both players separately
                            message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is not a miner, you lost the battle."
                            self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                            message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is not a miner, you won the battle."
                            self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    elif target_piece['rank'] == 'Flag':
                        self.board[dest_row][dest_col] = attacking_piece
                        self.board[src_row][src_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[player_id].append((dest_row, dest_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))
                        ## game over
                        self.state.set_winner(player_id=player_id,reason=[f"Player {player_id} has captured the opponent's flag!"])
                    elif attacking_piece['rank'] == 'Spy' and target_piece['rank'] == 'Marshal':
                        ## Spy beats Marshal only if spy attacks first
                        self.board[dest_row][dest_col] = attacking_piece
                        self.board[src_row][src_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[player_id].append((dest_row, dest_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))

                        ## add the observation to both players separately
                        message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a spy and the destination is a marshall, you won the battle."
                        self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a spy and the destination is a marshall, you lost the battle."
                        self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                    elif attacking_rank > target_rank:
                        ## attacker wins
                        self.board[dest_row][dest_col] = attacking_piece
                        self.board[src_row][src_col] = None
                        self.player_pieces[player_id].remove((src_row, src_col))
                        self.player_pieces[player_id].append((dest_row, dest_col))
                        self.player_pieces[1 - player_id].remove((dest_row, dest_col))

                        ## add the observation to both players separately
                        message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a higher rank than the destination, you won the battle."
                        self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                        message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a higher rank than the destination, you lost the battle."
                        self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

            else:
                ## defender wins
                self.board[src_row][src_col] = None
                self.player_pieces[player_id].remove((src_row, src_col))

                ## add the observation to both players separately
                message=f"You have moved your piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a lower rank than the destination, you lost the battle."
                self.state.add_observation(from_id=-1, to_id=player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)

                message=f"Player {player_id} has moved a piece from {source} to {dest}. The attacking piece was {attacking_piece['rank']} and the destination piece was {target_piece['rank']}. As the attacker is a lower rank than the destination, you won the battle."
                self.state.add_observation(from_id=-1, to_id=1-player_id, message=message, observation_type=ta.ObservationType.GAME_ACTION_DESCRIPTION)
        else:
            try:
                self.state.game_info[player_id]["invalid_move"] = True
            except Exception:
                pass
            self.state.set_winner(player_id=(1 - player_id), reason="Illegal move.")
            return self.state.step()

        ## check if the game is over
        if self._check_winner():
            reason=f"Player {self._check_winner()} wins! Player {1 - self._check_winner()} has no more movable pieces."
            self.state.set_winner(player_id=self._check_winner(), reason=reason)

        ## update the rendered board
        self.state.game_state["rendered_board"] = self._render_board(player_id=player_id, full_board=True)

        result = self.state.step()
        self._observe_current_state()
        return result
    
    # -------------------------------------------------------------------------
    # 3) RESET (override because original uses fixed 10×10 rows)
    # -------------------------------------------------------------------------
    def reset(self, num_players: int, seed: Optional[int]=None):
        """Reset but repopulate board using our custom placement logic."""
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)

        # custom board population
        self.board = self._populate_board()

        rendered = self._render_board(player_id=None, full_board=True)
        state_info = {
            "board": self.board,
            "player_pieces": self.player_pieces,
            "rendered_board": rendered,
        }

        self.state.reset(
            game_state=state_info,
            player_prompt_function=self._generate_player_prompt
        )
        self._observe_current_state()

    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]):
        """
        Generates the player prompt for the current player.

        Args:
            player_id (int): The ID of the current player.
            game_state (Dict[str, Any]): The current game state.
        """
        prompt = (
            f"You are Player {player_id} in Stratego.\n"
            "Your goal is to capture your opponent's Flag or eliminate all of their movable pieces.\n"
            "Your army has been placed for you on the board, including your Flag, Bombs, and other pieces of varying ranks.\n"
            "\n"
            "### Gameplay Instructions\n"
            "1. **Movement Rules:**\n"
            "   - On your turn, you can move one piece by one step to an adjacent square (up, down, left, or right) that is already occupied with your pieces.\n"
            "   - Example: A piece can move from A1 to B1 or A1 to A2 if B1 and A2 are not placed with the player's own pieces.\n"
            "   - If the selected piece is a Bomb or a Flag, it cannot be moved.\n"
            # "   - **Scout Movement:** Scouts, on the other hand, can move multiple steps in a straight line (horizontally or vertically), but strictly only on one condition.\n"
            # "       - The condition is that Scouts cannot jump over any piece (your own or your opponent's).\n"
            # "       - Example: If there is a piece between the Scout and its destination, the Scout cannot move to the destination.\n"
            # "       - This will be indicated as an invalid move which makes you lose the game.\n"
            "2. **Battles:**\n"
            "   - If you move onto a square occupied by an opponent's piece, then a battle will occur:\n"
            "     - The piece with the higher rank wins and eliminates the opponent's piece.\n"
            "     - If the ranks are equal, both pieces are removed from the board.\n"
            "     - **Special Cases:**\n"
            "       - Bombs eliminate most attacking pieces except Miners, which defuse Bombs.\n"
            "       - Spies can defeat the Marshal if the Spy attacks first but lose to all other pieces.\n"
            "3. **Strategic Goals:**\n"
            "   - Identify your opponent's pieces through their movements and battles.\n"
            "   - Protect your Flag while attempting to capture your opponent's Flag.\n"
            "   - Use Scouts strategically to gain information about your opponent's pieces and attack weak ones.\n"
            "\n"
            "### How to Make a Move:\n"
            "1. Specify the coordinates of the piece you want to move and its destination.\n"
            "2. Use the format: [A0 B0], where A0 is the source position, and B0 is the destination.\n"
            "   - Example: To move a piece from row 0, column 0 to row 1, column 0, input [A0 B0].\n"
            "3. Ensure the destination is valid according to the movement rules above.\n"
            "\n"
            "### Important Notes:\n"
            "- The board will show your pieces and their positions, e.g. MN, MS.\n"
            "- The board will also show known positions of your opponent's pieces without revealing their ranks, e.g. ?.\n"
            "- Grids with ~ are lakes and cannot be moved onto.\n"
            "- As a suggestion, start your game by moving your pieces that are on the front lines to gain information about your opponent's pieces. Player 0 and player 1's frontlines are row D and G respectively.\n"
            "\n"
            "Here is the current board state:\n"
        )
        return prompt

    def _observe_current_state(self):
        """
        Observe the current state of the game and update the state with the rendered board
        and gives the available moves for the current player.
        """
        player_id = self.state.current_player_id
        available_moves = []

        for row in range(self.size):
            for col in range(self.size):
                piece = self.board[row][col]
                if isinstance(piece, dict) and piece['player'] == player_id:
                    # Skip immovable pieces
                    if piece['rank'].lower() in ['bomb', 'flag']:
                        continue

                    # Check if this is a scout (can move multiple squares)
                    is_scout = piece['rank'].lower() == 'scout'
                    
                    # Check all four directions
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if is_scout:
                            # Scout can move multiple squares in this direction
                            distance = 1
                            while True:
                                new_row = row + (dr * distance)
                                new_col = col + (dc * distance)
                                
                                # Check if still within board bounds
                                if not (0 <= new_row < self.size and 0 <= new_col < self.size):
                                    break
                                
                                target = self.board[new_row][new_col]
                                
                                if target is None:
                                    # Empty square - scout can move here and continue
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                    distance += 1
                                elif isinstance(target, dict) and target['player'] != player_id:
                                    # Enemy piece - scout can attack but cannot continue past
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                    break
                                else:
                                    # Own piece or other obstacle - scout cannot move here or past
                                    break
                        else:
                            # Regular piece - can only move one square
                            new_row, new_col = row + dr, col + dc
                            if 0 <= new_row < self.size and 0 <= new_col < self.size:
                                target = self.board[new_row][new_col]
                                if (target is None or
                                    (isinstance(target, dict) and target['player'] != player_id)):
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")

        self.state.add_observation(
            message=f"Current Board:\n\n{self._render_board(player_id=player_id, full_board=False)}\nAvailable Moves: " + ", ".join(available_moves),
            observation_type=ta.ObservationType.GAME_BOARD
        )
    
    def _render_board(self, player_id, full_board: bool = False):
        """
        Renders the board state with fixed-width formatting for uniform alignment.

        Args:
            player_id (int): The player viewing the board.
            full_board (bool): Whether to render the full board or just the visible pieces.
        """
        # Define abbreviations for each piece
        piece_abbreviations = {
            'Flag': 'FL', 'Bomb': 'BM', 'Spy': 'SP', 'Scout': 'SC', 'Miner': 'MN',
            'Sergeant': 'SG', 'Lieutenant': 'LT', 'Captain': 'CP', 'Major': 'MJ',
            'Colonel': 'CL', 'General': 'GN', 'Marshal': 'MS'
        }

        res = []
        column_headers = "   " + " ".join([f"{i:>3}" for i in range(self.size)])  # Align column numbers
        res.append(column_headers + "\n")

        for row in range(self.size):
            row_label = chr(row + 65)  # Convert row index to a letter (A, B, C, ...)
            row_render = [f"{row_label:<3}"]  # Add row label with fixed width
            for col in range(self.size):
                if (row, col) in self.lakes:
                    cell = "  ~ "  # Lakes
                elif self.board[row][col] is None:
                    cell = "  . "  # Empty space
                else:
                    piece = self.board[row][col]
                    abbreviation = piece_abbreviations[piece['rank']]
                    if full_board:
                        cell = f" {abbreviation.lower() if piece['player'] == 0 else abbreviation.upper()} "  # Full board view
                    elif piece['player'] == player_id:
                        displayed_piece = abbreviation.upper()
                        cell = f" {displayed_piece} "
                    else:
                        cell = "  ? "  # Hidden opponent piece
                row_render.append(cell)

            res.append("".join(row_render) + "\n")

        return "".join(res)

    # -------------------------------------------------------------------------
    # 4) POPULATE BOARD (size-aware)
    # -------------------------------------------------------------------------
    def _populate_board(self):
        """
        Simplified placement:
        - Top `setup_rows` belong to Player 0
        - Bottom `setup_rows` belong to Player 1
        - No lakes on player's starting rows
        - Random placement within each player's zone
        """
        size = self.size
        setup_rows = max(2, size // 4)

        # clear board
        board = [[None for _ in range(size)] for _ in range(size)]

        for player in (0, 1):
            if player == 0:
                rows_allowed = range(0, setup_rows)
            else:
                rows_allowed = range(size - setup_rows, size)

            # place flag
            placed_flag = False
            while not placed_flag:
                r = random.choice(list(rows_allowed))
                c = random.randint(0, size - 1)
                if (r, c) not in self.lakes and board[r][c] is None:
                    board[r][c] = {"rank": "Flag", "player": player}
                    self.player_pieces[player].append((r, c))
                    placed_flag = True

            # place bombs
            bombs_to_place = self.piece_counts["Bomb"]
            while bombs_to_place > 0:
                r = random.choice(list(rows_allowed))
                c = random.randint(0, size - 1)
                if (r, c) not in self.lakes and board[r][c] is None:
                    board[r][c] = {"rank": "Bomb", "player": player}
                    self.player_pieces[player].append((r, c))
                    bombs_to_place -= 1

            # place remaining pieces
            for piece, count in self.piece_counts.items():
                if piece in ("Flag", "Bomb"):
                    continue
                for _ in range(count):
                    while True:
                        r = random.choice(list(rows_allowed))
                        c = random.randint(0, size - 1)
                        if (r, c) not in self.lakes and board[r][c] is None:
                            board[r][c] = {"rank": piece, "player": player}
                            self.player_pieces[player].append((r, c))
                            break

        # place lakes
        for r, c in self.lakes:
            board[r][c] = "~"

        return board


    # -------------------------------------------------------------------------
    # 5) VALIDATION OVERRIDE (only size-boundaries change)
    # -------------------------------------------------------------------------
    def _validate_move(self, player_id, src_r, src_c, dst_r, dst_c):
        
        if not (0 <= src_r < self.size and 0 <= src_c < self.size and 0 <= dst_r < self.size and 0 <= dst_c < self.size):
            reason=f"Invalid action format. Player {player_id} did not input valid coordinates."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if self.board[src_r][src_c] is None or self.board[src_r][src_c]['player'] != player_id:
            reason=f"Invalid action format. Player {player_id} must move one of their own pieces."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if abs(src_r - dst_r) + abs(src_c - dst_c) != 1 and self.board[src_r][src_c]['rank'].lower() == 'scout':
            ## check if there's a piece in between the source and destination
            if src_r == dst_r:
                for col in range(min(src_c, dst_c) + 1, max(src_c, dst_c)):
                    if self.board[src_r][col] is not None:
                        reason=f"Invalid action format. Player {player_id} cannot move a scout through other pieces."
                        self.state.set_invalid_move(reason=reason)
                        return False
            elif src_c == dst_c:
                for row in range(min(src_r, dst_r) + 1, max(src_r, dst_r)):
                    if self.board[row][src_c] is not None:
                        reason=f"Invalid action format. Player {player_id} cannot move a scout through other pieces."
                        self.state.set_invalid_move(reason=reason)
                        return False
            else:
                reason=f"Invalid action format. Player {player_id} cannot move a scout diagonally."
                self.state.set_invalid_move(reason=reason)
                return False
            
        if abs(src_r - dst_r) + abs(src_c - dst_c) != 1 and self.board[src_r][src_c]['rank'].lower() != 'scout':
            ## !  - by right, only scouts can move more than one square at a time but we are not implementing that yet
            reason=f"Invalid action format. Pieces, apart from scouts, can only move one square at a time."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if self.board[dst_r][dst_c] is not None:
            if (dst_r, dst_c) in self.lakes:
                reason=f"Invalid action format. Player {player_id} cannot move into the lake."
                self.state.set_invalid_move(reason=reason)
                return False
            
            elif self.board[dst_r][dst_c]['player'] == player_id:
                reason=f"Invalid action format. Player {player_id} cannot move onto their own piece."
                self.state.set_invalid_move(reason=reason)
                return False
        
        if self.board[src_r][src_c]['rank'].lower() in ['bomb','flag']:
            reason=f"Invalid action format. Player {player_id} cannot move a bomb or flag."
            self.state.set_invalid_move(reason=reason)
            return False
        size = self.size

        if not (0 <= src_r < size and 0 <= src_c < size and
                0 <= dst_r < size and 0 <= dst_c < size):
            self.state.set_invalid_move("Invalid: out of board.")
            return False

        return True


    def _check_winner(self):
        """
        determine which player has no more pieces that are not bombs or flags.
        """
        for player in range(2):
            if all([self.board[row][col]['rank'] in ['Bomb', 'Flag'] for row, col in self.player_pieces[player]]):
                return 1 - player
        return None
