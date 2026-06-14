import numpy as np

class OthelloGame:
    def __init__(self):
        self.board_size = 8
        self.directions = [(-1, -1), (-1, 0), (-1, 1),
                           (0, -1),          (0, 1),
                           (1, -1), (1, 0), (1, 1)]
        self.reset()

    def reset(self):
        self.current_player = 1
        self.board = np.zeros((self.board_size, self.board_size), dtype=int)
        self.board[3][3] = -1
        self.board[3][4] = 1
        self.board[4][3] = 1
        self.board[4][4] = -1
        self.is_done = False
        self.winner = None

    def step(self, row, col):
        if self.is_done:
            return False

        if not self.is_valid_move(row, col):
            return False
        
        self.flip_pieces(row, col)
        self.change_turn()
        return True
    
    def is_valid_move(self, row, col, player = None):
        if player is None:
            player = self.current_player
        
        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
            return False
        
        if self.board[row][col] != 0:
            return False
        
        for dr, dc in self.directions:
            r, c = row + dr, col + dc
            found_opponent = False

            while 0 <= r < self.board_size and 0 <= c < self.board_size:
                current_cell = self.board[r][c]
                if current_cell == 0:
                    break
                if current_cell == player:
                    if found_opponent:
                        return True
                    else:
                        break
                else:
                    found_opponent = True
                r += dr
                c += dc
        return False
    
    def flip_pieces(self, row, col):
        self.board[row][col] = self.current_player
        for dr, dc in self.directions:
            r, c = row + dr, col + dc
            pieces_to_flip = []

            while 0 <= r < self.board_size and 0 <= c < self.board_size:
                current_cell = self.board[r][c]
                if current_cell == 0:
                    break
                if current_cell == self.current_player:
                    for rr, cc in pieces_to_flip:
                        self.board[rr][cc] = self.current_player
                    break
                else:
                    pieces_to_flip.append((r, c))
                r += dr
                c += dc
    
    def change_turn(self):
        opponent = self.current_player * -1
        if self.has_valid_moves(opponent):
            self.current_player = opponent
        elif self.has_valid_moves(self.current_player):
            pass  # 相手に合法手がない場合は自分のターンが続く
        else:
            self.is_done = True
            self.calculate_winner()

    def has_valid_moves(self, player):
        for r in range(self.board_size):
            for c in range(self.board_size):
                if self.is_valid_move(r, c, player):
                    return True
        return False
        

    def calculate_winner(self):
        black_count = np.sum(self.board == 1)
        white_count = np.sum(self.board == -1)
        if black_count > white_count:
            self.winner = 1
        elif white_count > black_count:
            self.winner = -1
        else:
            self.winner = 0  # 引き分け

    def get_observation(self, player=None):
        if player is None:
            player = self.current_player

        my_stones = (self.board == player).astype(int)
        opponent_stones = (self.board == -player).astype(int)
        legal_moves_mask = np.zeros((self.board_size, self.board_size), dtype=int)

        for row in range(self.board_size):
            for col in range(self.board_size):
                if self.is_valid_move(row, col, player):
                    legal_moves_mask[row][col] = 1

        obs = np.stack([my_stones, opponent_stones, legal_moves_mask])
        return obs





        


