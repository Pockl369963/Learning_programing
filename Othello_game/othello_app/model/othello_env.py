from typing import List, Tuple, Dict

# Player constants
EMPTY = 0
PLAYER_BLACK = 1
PLAYER_WHITE = -1


class OthelloEnv:
    """Othello game engine that manages board state and game rules."""

    EMPTY = EMPTY
    PLAYER_BLACK = PLAYER_BLACK
    PLAYER_WHITE = PLAYER_WHITE

    # 8 directions for searching (row_offset, col_offset)
    _DIRECTIONS: List[Tuple[int, int]] = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]

    def _validate_board(self, board: List[List[int]]) -> None:
        """盤面データが正しい形式（8x8の2次元配列で、0, 1, -1のみを含む）か検証します。"""
        if not isinstance(board, list) or len(board) != 8:
            raise ValueError("盤面は要素数8のリストである必要があります。")
        for row in board:
            if not isinstance(row, list) or len(row) != 8:
                raise ValueError("盤面の各行は要素数8のリストである必要があります。")
            for cell in row:
                if cell not in (self.EMPTY, self.PLAYER_BLACK, self.PLAYER_WHITE):
                    raise ValueError(f"不正な盤面データが含まれています: {cell}")

    def _is_on_board(self, row: int, col: int) -> bool:
        """指定された座標が盤面上にあるか判定します。"""
        return 0 <= row < 8 and 0 <= col < 8

    def get_initial_board(self) -> List[List[int]]:
        """8x8の初期盤面を生成します。

        Returns:
            List[List[int]]: 0=空, 1=黒, -1=白で構成される8x8の2次元配列
        """
        board = [[self.EMPTY] * 8 for _ in range(8)]
        board[3][3], board[4][4] = self.PLAYER_WHITE, self.PLAYER_WHITE
        board[3][4], board[4][3] = self.PLAYER_BLACK, self.PLAYER_BLACK
        return board

    def _get_flippable_discs(
        self, board: List[List[int]], player: int, row: int, col: int
    ) -> List[Tuple[int, int]]:
        """指定された座標に石を置いた際に裏返せる石の座標リストを取得します。

        Args:
            board (List[List[int]]): 現在の盤面データ
            player (int): 現在の手番（1 または -1）
            row (int): 石を置く行（0〜7）
            col (int): 石を置く列（0〜7）

        Returns:
            List[Tuple[int, int]]: 裏返せる石の座標(row, col)のリスト
        """
        self._validate_board(board)

        if not self._is_on_board(row, col):
            return []
        if board[row][col] != self.EMPTY:
            return []
        if player not in (self.PLAYER_BLACK, self.PLAYER_WHITE):
            return []

        flippable = []
        opponent = (
            self.PLAYER_WHITE if player == self.PLAYER_BLACK else self.PLAYER_BLACK
        )

        # 8方向への探索を行い、裏返せる石を見つける
        for dr, dc in self._DIRECTIONS:
            r, c = row + dr, col + dc
            temp_flippable = []

            # 隣接する石が相手の石である限り、探索を続ける
            while self._is_on_board(r, c) and board[r][c] == opponent:
                temp_flippable.append((r, c))
                r += dr
                c += dc

            # 相手の石を挟んだ先に自分の石があれば、裏返せる石として確定する
            if self._is_on_board(r, c) and board[r][c] == player and temp_flippable:
                flippable.extend(temp_flippable)

        return flippable

    def is_valid_move(
        self, board: List[List[int]], player: int, row: int, col: int
    ) -> bool:
        """指定された座標に石を置くことが合法手かどうかを判定します。

        Args:
            board (List[List[int]]): 現在の盤面データ
            player (int): 現在の手番（1 または -1）
            row (int): 石を置く行（0〜7）
            col (int): 石を置く列（0〜7）

        Returns:
            bool: 合法手であればTrue、そうでなければFalse
        """
        try:
            return len(self._get_flippable_discs(board, player, row, col)) > 0
        except ValueError:
            return False

    def apply_move(
        self, board: List[List[int]], player: int, row: int, col: int
    ) -> List[List[int]]:
        """指定された座標に石を置き、石を裏返した後の新しい盤面を返します。

        Args:
            board (List[List[int]]): 現在の盤面データ
            player (int): 現在の手番（1 または -1）
            row (int): 石を置く行（0〜7）
            col (int): 石を置く列（0〜7）

        Returns:
            List[List[int]]: 更新された新しい盤面データ

        Raises:
            ValueError: 盤面外、既に石がある、または合法手でない場合
        """
        self._validate_board(board)

        if not self._is_on_board(row, col):
            raise ValueError(f"座標({row}, {col})は盤面外です。")
        if board[row][col] != self.EMPTY:
            raise ValueError(f"座標({row}, {col})にはすでに石が置かれています。")

        flippable = self._get_flippable_discs(board, player, row, col)
        if not flippable:
            raise ValueError(
                f"座標({row}, {col})に石を置くことはできません。裏返せる石がありません。"
            )

        # 副作用を避けるため、盤面をディープコピーして更新する
        new_board = [r[:] for r in board]
        new_board[row][col] = player
        for r, c in flippable:
            new_board[r][c] = player

        return new_board

    def has_valid_moves(self, board: List[List[int]], player: int) -> bool:
        """指定されたプレイヤーに合法手があるかどうかを判定します。

        Args:
            board (List[List[int]]): 現在の盤面データ
            player (int): 現在の手番（1 または -1）

        Returns:
            bool: 合法手が存在すればTrue、そうでなければFalse
        """
        self._validate_board(board)
        for row in range(8):
            for col in range(8):
                if board[row][col] == self.EMPTY and self.is_valid_move(
                    board, player, row, col
                ):
                    return True
        return False

    def change_turn(self, player: int) -> int:
        """手番を交代します。

        Args:
            player (int): 現在の手番（1 または -1）

        Returns:
            int: 交代後の手番（-1 または 1）

        Raises:
            ValueError: プレイヤーの値が不正な場合
        """
        if player not in (self.PLAYER_BLACK, self.PLAYER_WHITE):
            raise ValueError(f"不正なプレイヤー値です: {player}")
        return self.PLAYER_WHITE if player == self.PLAYER_BLACK else self.PLAYER_BLACK

    def calculate_winner(self, board: List[List[int]]) -> Dict[str, int]:
        """盤面から黒と白の石の数を計算し、勝敗を判定します。

        Args:
            board (List[List[int]]): 現在の盤面データ

        Returns:
            Dict[str, int]: 黒の数、白の数、勝者の情報を格納した辞書。
                形式: {"black": 黒の数, "white": 白の数, "winner": 勝者(1, -1, 0(引き分け))}
        """
        self._validate_board(board)

        black_count = sum(row.count(self.PLAYER_BLACK) for row in board)
        white_count = sum(row.count(self.PLAYER_WHITE) for row in board)

        if black_count > white_count:
            winner = self.PLAYER_BLACK
        elif white_count > black_count:
            winner = self.PLAYER_WHITE
        else:
            winner = self.EMPTY

        return {"black": black_count, "white": white_count, "winner": winner}
