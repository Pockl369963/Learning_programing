from typing import List

# Player constants
PLAYER_BLACK = 1
PLAYER_WHITE = -1
EMPTY = 0


def get_initial_board() -> List[List[int]]:
    """8x8の初期盤面を生成します。

    Returns:
        List[List[int]]: 0=空, 1=黒, -1=白で構成される8x8の2次元配列
    """
    board = [[EMPTY] * 8 for _ in range(8)]
    board[3][3], board[4][4] = PLAYER_WHITE, PLAYER_WHITE
    board[3][4], board[4][3] = PLAYER_BLACK, PLAYER_BLACK
    return board
