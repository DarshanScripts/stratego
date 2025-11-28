import re, random
from typing import Optional, Dict, Tuple, List, Any

import textarena as ta

class StrategoDuelEnv(ta.Env):
    """ A two-player implementation of the board game Stratego on a 6x6 board """
    def __init__(self):
        """
        Initialize the environment for a 6x6 board size.
        """
        ## set up the board items (Reduced piece counts for 6x6 play)
        # Note: We reduce the piece count significantly (from 40 to 7 per side)
        # to fit a smaller board and focus on a duel setup.
        self.piece_counts = {
            'Flag': 1, 'Bomb': 2, 'Spy': 1, 'Scout': 1, 'Miner': 1,
            'General': 1, 'Marshal': 1
        }
        self.piece_ranks = {
            'Flag': 0, 'Bomb': 11, 'Spy': 1, 'Scout': 2, 'Miner': 3,
            'General': 9, 'Marshal': 10
        }
        
        # New lake coordinates for a 6x6 board (Rows 0-5, Cols 0-5).
        # This creates a central 2x2 lake at the intersection of rows 2, 3 and columns 2, 3.
        self.lakes = [(2, 2), (2, 3), (3, 2), (3, 3)]
        
        self.player_pieces = {0: [], 1: []}
        
        # Initializes a 6-row by 6-column board (36 total squares).
        self.board = [[None for _ in range(6)] for _ in range(6)]

    @property
    def terminal_render_keys(self):
        return ["rendered_board"]

    def reset(self, num_players: int, seed: Optional[int]=None):
        """ Reset the environment to start a new game """
        self.state = ta.TwoPlayerState(num_players=num_players, seed=seed)
        # (13 Nov 2025) New Comment : reset the turn counter at the start of a new game.
        self.turn_count = 0
        
        ## populate the board
        self.board = self._populate_board()

        ## initialise the game state
        rendered_board = self._render_board(player_id=None, full_board=True)
        game_state={"board": self.board, "player_pieces": self.player_pieces, "rendered_board": rendered_board}
        self.state.reset(game_state=game_state, player_prompt_function=self._generate_player_prompt)
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
            "   - On your turn, you can move one piece by one step to an adjacent square (up, down, left, or right) that is already occupied with your pieces.\n"
            "   - Example: A piece can move from A0 to B0 or A0 to A1 if B0 and A1 are not placed with the player's own pieces.\n"
            "   - If the selected piece is a Bomb or a Flag, it cannot be moved.\n"
            "2. **Battles:**\n"
            "   - If you move onto a square occupied by an opponent's piece, then a battle will occur:\n"
            "     - The piece with the higher rank wins and eliminates the opponent's piece.\n"
            "     - If the ranks are equal, both pieces are removed from the board.\n"
            "     - **Special Cases:**\n"
            "       - Bombs eliminate most attacking pieces except Miners, which defuse Bombs.\n"
            "       - Spies can defeat the Marshal if the Spy attacks first but lose to all other pieces.\n"
            "3. **Strategic Goals:**\n"
            "   - Identify your opponent's pieces through their movements and battles.\n"
            "   - Protect your Flag while attempting to capture your opponent's Flag.\n"
            "   - Use Scouts strategically to gain information about your opponent's pieces and attack weak ones.\n"
            "\n"
            "### How to Make a Move:\n"
            "1. Specify the coordinates of the piece you want to move and its destination.\n"
            "2. Use the format: [A0 B0], where A0 is the source position, and B0 is the destination.\n"
            "   - Example: To move a piece from row 0, column 0 to row 1, column 0, input [A0 B0].\n"
            "3. Ensure the destination is valid according to the movement rules above.\n"
            "\n"
            "### Important Notes:\n"
            "- The board will show your pieces and their positions, e.g. MN, MS.\n"
            "- The board will also show known positions of your opponent's pieces without revealing their ranks, e.g. ?.\n"
            "- Grids with ~ are lakes and cannot be moved onto.\n"
            f"- As a suggestion, start your game by moving your pieces that are on the front lines to gain information about your opponent's pieces. Player 0's frontline is **row 1** and player 1's frontline is **row 4**.\n"
            "\n"
            "Here is the current board state:\n"
        )
        return prompt

    def _observe_current_state(self):
        """
        Observe the current state of the game and update the state with the rendered board
        and gives the available moves for the current player.
        """
        BOARD_SIZE = 6 # Added constant for 6x6 consistency
        
        player_id = self.state.current_player_id
        available_moves = []

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
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
                                if not (0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE):
                                    break
                                
                                target = self.board[new_row][new_col]
                                
                                # Check for lake (impassable obstacle)
                                if (new_row, new_col) in self.lakes:
                                    break 

                                if target is None or target == "~":
                                    # Empty square or lake - scout can move here and continue (if empty)
                                    # If target is "~" (lake), we break, but need to check for lake first.
                                    if target is None:
                                        available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                        distance += 1
                                    else: # It's a lake, stop
                                        break
                                        
                                elif isinstance(target, dict) and target['player'] != player_id:
                                    # Enemy piece - scout can attack but cannot continue past
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")
                                    break
                                else:
                                    # Own piece or other obstacle (not lake, as lake is checked above) - scout cannot move here or past
                                    break
                        else:
                            # Regular piece - can only move one square
                            new_row, new_col = row + dr, col + dc
                            if 0 <= new_row < BOARD_SIZE and 0 <= new_col < BOARD_SIZE:
                                # Check for lake
                                if (new_row, new_col) in self.lakes:
                                    continue
                                    
                                target = self.board[new_row][new_col]
                                if (target is None or
                                    (isinstance(target, dict) and target['player'] != player_id)):
                                    available_moves.append(f"[{chr(row + 65)}{col} {chr(new_row + 65)}{new_col}]")


        # new comment(13 Nov 2025) Store the number of available moves in the game state.
        # This is critical for detecting a "no moves remaining" loss or a stalemate/draw.
        num_available_moves = len(available_moves)
        self.state.game_state[f'available_moves_p{player_id}'] = num_available_moves

        #Previous code lines for the observation message
        self.state.add_observation(
            message=f"Current Board:\n\n{self._render_board(player_id=player_id, full_board=False)}\nAvailable Moves: " + ", ".join(available_moves),
            observation_type=ta.ObservationType.GAME_BOARD
        )
    
    def _populate_board(self):
        """
        Populates the board with pieces for each player strategically on the 6x6 board.
        """
        BOARD_SIZE = 6 # Constant for board size
        
        for player in range(2):
            # Define rows for each player on the 6x6 board:
            # P0 setup zone: Rows 0 and 1
            # P1 setup zone: Rows 4 and 5
            player_setup_rows = range(0, 2) if player == 0 else range(4, 6)
            
            # --- Flag Placement ---
            # Place the Flag strategically
            while True:
                row = random.choice(player_setup_rows)
                col = random.randint(0, BOARD_SIZE - 1)
                if (row, col) not in self.lakes and self.board[row][col] is None:
                    self.board[row][col] = {'rank': 'Flag', 'player': player}
                    self.player_pieces[player].append((row, col))
                    flag_position = (row, col)
                    break

            # --- Bomb Placement (Adjacent to Flag) ---
            bombs_to_place = self.piece_counts['Bomb']
            bomb_positions = [
                (flag_position[0] + dr, flag_position[1] + dc)
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Adjacent cells
                if 0 <= flag_position[0] + dr < BOARD_SIZE and 0 <= flag_position[1] + dc < BOARD_SIZE # Check 6x6 bounds
            ]

            for pos in bomb_positions:
                # Ensure placement is within the player's setup zone
                if (bombs_to_place > 0 and self.board[pos[0]][pos[1]] is None and 
                    pos not in self.lakes and pos[0] in player_setup_rows):
                    
                    self.board[pos[0]][pos[1]] = {'rank': 'Bomb', 'player': player}
                    self.player_pieces[player].append(pos)
                    bombs_to_place -= 1

            # --- Place remaining Bombs (Randomly in setup rows) ---
            for _ in range(bombs_to_place):
                while True:
                    row = random.choice(player_setup_rows) # Use correct player rows
                    col = random.randint(0, BOARD_SIZE - 1) # Corrected column range (0 to 5)
                    if self.board[row][col] is None and (row, col) not in self.lakes:
                        self.board[row][col] = {'rank': 'Bomb', 'player': player}
                        self.player_pieces[player].append((row, col))
                        break

            # --- Place other pieces randomly ---
            for piece, count in self.piece_counts.items():
                if piece in ['Flag', 'Bomb']:
                    continue  # Skip already placed pieces
                for _ in range(count):
                    while True:
                        row = random.choice(player_setup_rows) # Use correct player rows
                        col = random.randint(0, BOARD_SIZE - 1) # Corrected column range (0 to 5)
                        if self.board[row][col] is None and (row, col) not in self.lakes:
                            self.board[row][col] = {'rank': piece, 'player': player}
                            self.player_pieces[player].append((row, col))
                            break

        # Place the lakes marker (~)
        for row, col in self.lakes:
            self.board[row][col] = "~"

        return self.board

    
    def _render_board(self, player_id, full_board: bool = False):
        """
        Renders the board state with fixed-width formatting for uniform alignment.

        Args:
            player_id (int): The player viewing the board.
            full_board (bool): Whether to render the full board or just the visible pieces.
        """
        BOARD_SIZE = 6 # Added constant for 6x6 consistency
        
        # Define abbreviations for each piece
        piece_abbreviations = {
            'Flag': 'FL', 'Bomb': 'BM', 'Spy': 'SP', 'Scout': 'SC', 'Miner': 'MN',
            'General': 'GN', 'Marshal': 'MS' # Only using 6x6 pieces
        }

        res = []
        # Update column headers to range from 0 to 5 (size 6)
        column_headers = "   " + " ".join([f"{i:>3}" for i in range(BOARD_SIZE)])  
        res.append(column_headers + "\n")

        for row in range(BOARD_SIZE): # Iterate over 6 rows
            row_label = chr(row + 65)  # Convert row index to a letter (A-F)
            row_render = [f"{row_label:<3}"]  # Add row label with fixed width
            for col in range(BOARD_SIZE): # Iterate over 6 columns
                if (row, col) in self.lakes:
                    cell = "  ~ "  # Lakes
                elif self.board[row][col] is None:
                    cell = "  . "  # Empty space
                else:
                    piece = self.board[row][col]
                    # Handle the case where the piece is the lake marker "~"
                    if piece == "~":
                        cell = "  ~ "
                    else:
                        abbreviation = piece_abbreviations.get(piece['rank'], piece['rank'][:2].upper())
                        if full_board:
                            cell = f" {abbreviation.lower() if piece['player'] == 0 else abbreviation.upper()} "  # Full board view
                        elif piece['player'] == player_id:
                            displayed_piece = abbreviation.upper()
                            cell = f" {displayed_piece} "
                        else:
                            cell = "  ? "  # Hidden opponent piece
                row_render.append(cell)

            res.append("".join(row_render) + "\n")

        return "".join(res)



    def step(self, action: str) -> Tuple[bool, ta.Info]:
        # new comment(13 Nov 2025) Increment turn counter
        self.turn_count += 1
        player_id = self.state.current_player_id

        # new comment(13 Nov 2025) This block fixes Bug #3 (No Moves Remaining).
        # We check if the player has 0 moves *before* parsing their action.
        # This prevents an 'Invalid action' penalty when they have no valid moves.
        num_moves = self.state.game_state.get(f'available_moves_p{player_id}', 1) # Default to 1 to avoid error
        if num_moves == 0:
            # The current player cannot move. Check if the *other* player can.
            if self._has_movable_pieces(1 - player_id):
                # Opponent still has pieces, so current player loses.
                reason = f"Player {player_id} has no valid moves remaining. Player {1 - player_id} wins!"
                self.state.set_winner(player_id=(1 - player_id), reason=reason)
            else:
                # Neither player can move. This is a stalemate (draw).
                reason = "Stalemate: Neither player has any valid moves remaining. The game is a draw."
                self.state.set_winner(player_id=-1, reason=reason) # -1 means draw
            
            # Immediately end the game
            return self.state.step()
        
        # previous code for executing the action

        """ Execute an action in the environment """
        player_id = self.state.current_player_id

        ## update the observation
        self.state.add_observation(from_id=player_id, to_id=player_id, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

        ## action search pattern
        # Updated pattern to only allow columns 0-5 and rows A-F
        action_search_pattern = re.compile(r"\[([A-F])([0-5]) ([A-F])([0-5])\]", re.IGNORECASE) 
        match = action_search_pattern.search(action)

        if match is None:
            reason=f"Invalid action format. Player {player_id} did not input a move in the format [A0 B0] (or coordinates are outside the 6x6 board)."
            self.state.set_invalid_move(reason=reason)
        
        else:
            src_row, src_col, dest_row, dest_col = match.groups()
            src_row, dest_row = src_row.upper(), dest_row.upper()
            source = f"{src_row}{src_col}"
            dest = f"{dest_row}{dest_col}"
            src_row, src_col = ord(src_row) - 65, int(src_col)
            dest_row, dest_col = ord(dest_row) - 65, int(dest_col)
            
            BOARD_SIZE = 6 # Constant for 6x6 consistency

            ## check if the source and destination are valid
            if self._validate_move(player_id=player_id, src_row=src_row, src_col=src_col, dest_row=dest_row, dest_col=dest_col):

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

                            # (12 Nov 2025)👇 ADD THIS LINE: Remove the Bomb's coordinate from the defender's list
                            self.player_pieces[1 - player_id].remove((dest_row, dest_col))

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

                        # Changes below: for the Winner setting(12 Nov 2025)
                        reason=f"Player {player_id} has captured the opponent's flag!"
                        self.state.set_winner(player_id=player_id,reason=reason)

                        # Immediately end the game and return the final state
                        return self.state.step()


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

        # new comment(13 Nov 2025) This block checks for win/draw conditions
        # *after* a move has been successfully made.

        # 1. Check for Elimination Win (opponent has no movable pieces left)
        winner = self._check_winner()
        if winner is not None:
            reason=f"Player {winner} wins! Player {1 - winner} has no more movable pieces."
            self.state.set_winner(player_id=winner, reason=reason)

        # 2. Check for Stalemate (Draw)
        elif self._check_stalemate():
            reason = "Stalemate: Neither player has any valid moves remaining. The game is a draw."
            self.state.set_winner(player_id=-1, reason=reason) # -1 means draw
        
        # 3. Check for Turn Limit (Draw) - This fixes Bug #2
        elif self.turn_count > 1000: # You can adjust this number
            reason = f"Game ended in a draw (turn limit of 1000 moves exceeded)."
            self.state.set_winner(player_id=-1, reason=reason)

        ## update the rendered board
        self.state.game_state["rendered_board"] = self._render_board(player_id=player_id, full_board=True)

        result = self.state.step()
        
        # We must observe the *next* player's state *before* returning
        if not result[0]: # If game is not done
             self._observe_current_state()
             
        return result
    
    def _validate_move(self, player_id, src_row, src_col, dest_row, dest_col):
        """
        Validates the move based on the game rules.

        Args:
            player_id (int): The ID of the player making the move.
            src_row (int): The row of the source position.
            src_col (int): The column of the source position.
            dest_row (int): The row of the destination position.
            dest_col (int): The column of the destination position.
        """
        BOARD_SIZE = 6 # Constant for 6x6 consistency
        
        # 1. Check bounds against 6x6 board
        if not (0 <= src_row < BOARD_SIZE and 0 <= src_col < BOARD_SIZE and 0 <= dest_row < BOARD_SIZE and 0 <= dest_col < BOARD_SIZE):
            reason=f"Invalid action format. Player {player_id} did not input valid coordinates (must be A0-F5)."
            self.state.set_invalid_move(reason=reason)
            return False
        
        if self.board[src_row][src_col] is None or self.board[src_row][src_col]['player'] != player_id:
            reason=f"Invalid action format. Player {player_id} must move one of their own pieces."
            self.state.set_invalid_move(reason=reason)
            return False
        
        # 2. Check for Scout Movement (multiple steps in a straight line)
        if self.board[src_row][src_col]['rank'].lower() == 'scout':
            # Must move in a straight line (horizontal or vertical)
            is_horizontal = src_row == dest_row
            is_vertical = src_col == dest_col
            
            if not (is_horizontal or is_vertical):
                reason=f"Invalid action format. Player {player_id} cannot move a scout diagonally."
                self.state.set_invalid_move(reason=reason)
                return False
            
            # Check for pieces or lakes in between
            if is_horizontal:
                step = 1 if dest_col > src_col else -1
                for col in range(src_col + step, dest_col, step):
                    if self.board[src_row][col] is not None or (src_row, col) in self.lakes:
                        reason=f"Invalid action format. Player {player_id} cannot move a scout over other pieces or lakes."
                        self.state.set_invalid_move(reason=reason)
                        return False
            elif is_vertical:
                step = 1 if dest_row > src_row else -1
                for row in range(src_row + step, dest_row, step):
                    if self.board[row][src_col] is not None or (row, src_col) in self.lakes:
                        reason=f"Invalid action format. Player {player_id} cannot move a scout over other pieces or lakes."
                        self.state.set_invalid_move(reason=reason)
                        return False
                        
        # 3. Check for Regular Piece Movement (only one square)
        elif abs(src_row - dest_row) + abs(src_col - dest_col) != 1:
            reason=f"Invalid action format. Pieces, apart from scouts, can only move one square at a time."
            self.state.set_invalid_move(reason=reason)
            return False
        
        # 4. Check Destination
        if (dest_row, dest_col) in self.lakes:
            reason=f"Invalid action format. Player {player_id} cannot move into the lake."
            self.state.set_invalid_move(reason=reason)
            return False
        
        target = self.board[dest_row][dest_col]
        if target is not None and target != "~":
            if target['player'] == player_id:
                reason=f"Invalid action format. Player {player_id} cannot move onto their own piece."
                self.state.set_invalid_move(reason=reason)
                return False
        
        # 5. Check Immovable Pieces
        if self.board[src_row][src_col]['rank'].lower() in ['bomb','flag']:
            reason=f"Invalid action format. Player {player_id} cannot move a bomb or flag."
            self.state.set_invalid_move(reason=reason)
            return False
        
        return True
    
    #Working on below for new code to deal with Non Type error
    # def _check_winner(self):
    # 	 """
    # 	 determine which player has no more pieces that are not bombs or flags.
    # 	 """
    # 	 for player in range(2):
    # 		 if all([self.board[row][col]['rank'] in ['Bomb', 'Flag'] for row, col in self.player_pieces[player]]):
    # 		 	 return 1 - player
    # 	 return None

    def _check_winner(self):
        """
        Determine which player has no more pieces that are not bombs or flags.
        FIX: Skips coordinates that are empty on the board (already removed).
        """
        for player in range(2):
            # NEW LOGIC: Filter out None/empty squares before checking rank
            movable_pieces_remain = any([
                self.board[row][col] is not None and self.board[row][col] != "~" and self.board[row][col]['rank'] not in ['Bomb', 'Flag'] 
                for row, col in self.player_pieces[player]
            ])
            
            # Original logic: If NO movable pieces remain, the opponent (1 - player) wins.
            if not movable_pieces_remain:
                return 1 - player
        return None
    
    # new comment(13 Nov 2025) These are new helper methods for win/draw checking.

    def _has_movable_pieces(self, player_id: int) -> bool:
        """Helper function to check if a player has any movable pieces left."""
        # This uses the same logic as your _check_winner, just isolated
        return any([
            self.board[row][col] is not None and self.board[row][col] != "~" and self.board[row][col]['rank'] not in ['Bomb', 'Flag'] 
            for row, col in self.player_pieces[player_id]
        ])

    def _check_stalemate(self) -> bool:
        """
        Checks for two types of stalemate (draw):
        1. Neither player has any movable pieces left.
        2. Both players have 0 available moves (e.g., all pieces are blocked).
        """
        # 1. Check if both players are eliminated (e.g., last two pieces trade)
        p0_has_movable = self._has_movable_pieces(0)
        p1_has_movable = self._has_movable_pieces(1)
        if not p0_has_movable and not p1_has_movable:
            return True # Both players lost all pieces

        # 2. Check if both players are blocked (0 moves)
        # This relies on _observe_current_state being called
        p0_move_count = self.state.game_state.get('available_moves_p0', 1) # Default to 1
        p1_move_count = self.state.game_state.get('available_moves_p1', 1)
        
        if p0_move_count == 0 and p1_move_count == 0:
            return True # Both players are blocked
            
        return False