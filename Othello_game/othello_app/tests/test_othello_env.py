import copy
from typing import Any, List

import pytest

from model.othello_env import OthelloEnv


@pytest.fixture
def env() -> OthelloEnv:
    """OthelloEnvインスタンスを提供するフィクスチャ。"""
    return OthelloEnv()


@pytest.fixture
def initial_board() -> List[List[int]]:
    """初期状態の盤面を提供するフィクスチャ。盤面のテストのため一から定義"""
    board = [[0] * 8 for _ in range(8)]
    board[3][3], board[4][4] = -1, -1
    board[3][4], board[4][3] = 1, 1
    return board


@pytest.fixture
def mid_game_board() -> List[List[int]]:
    """複数方向が裏返せる複雑な盤面を提供するフィクスチャ。
    例: 黒(1)が(3, 2)に置くと、右方向と右下方向の白(-1)が裏返るような盤面。
    """
    board = [[0] * 8 for _ in range(8)]
    board[3][3], board[3][4] = -1, -1
    board[3][5] = 1
    board[4][3] = -1
    board[5][4] = 1
    return board


@pytest.fixture
def pass_board() -> List[List[int]]:
    """一方のプレイヤーに合法手がない状態を提供するフィクスチャ。"""
    board = [[1] * 8 for _ in range(8)]
    board[0][0] = 0
    return board


@pytest.fixture
def full_board() -> List[List[int]]:
    """石がすべて埋まった決着状態を提供するフィクスチャ。"""
    board = [[1] * 8 for _ in range(8)]
    board[0][0], board[0][1] = -1, -1
    return board


@pytest.fixture
def star_board() -> List[List[int]]:
    """全8方向の裏返しを検証するための「星型」盤面を提供するフィクスチャ。"""
    board = [[0] * 8 for _ in range(8)]
    for r, c in [(2, 2), (2, 3), (2, 4), (3, 2), (3, 4), (4, 2), (4, 3), (4, 4)]:
        board[r][c] = -1
    for r, c in [(1, 1), (1, 3), (1, 5), (3, 1), (3, 5), (5, 1), (5, 3), (5, 5)]:
        board[r][c] = 1
    return board


@pytest.fixture
def edge_board() -> List[List[int]]:
    """盤面の端（壁）での挙動を検証するためのフィクスチャ。"""
    board = [[0] * 8 for _ in range(8)]
    for c in range(1, 8):
        board[0][c] = -1

    board[7][0] = 1
    for c in range(1, 7):
        board[7][c] = -1
    return board


class TestGetInitialBoard:
    """get_initial_boardメソッドのテストスイート"""

    def test_get_initial_board(self, env: OthelloEnv) -> None:
        """
        [正常系] 初期盤面が正しく生成されること。

        Arrange:
            OthelloEnvインスタンスを利用する。
        Act:
            get_initial_board を実行する。
        Assert:
            - 盤面が 8x8 のリストであること。
            - 初期配置の4マス（中央）に正しく石が配置されていること。
            - 残りの60マスが空(0)であること。
        """
        # Arrange & Act
        board = env.get_initial_board()

        # Assert
        assert len(board) == 8
        assert all(len(row) == 8 for row in board)
        assert board[3][3] == OthelloEnv.PLAYER_WHITE
        assert board[4][4] == OthelloEnv.PLAYER_WHITE
        assert board[3][4] == OthelloEnv.PLAYER_BLACK
        assert board[4][3] == OthelloEnv.PLAYER_BLACK

        empty_count = sum(row.count(OthelloEnv.EMPTY) for row in board)
        assert empty_count == 60


class TestValidateBoard:
    """_validate_boardメソッドのテストスイート"""

    def test_valid_board(self, env: OthelloEnv, initial_board: List[List[int]]) -> None:
        """
        [正常系] 正しい形式の盤面がエラーなく通過すること。

        Arrange:
            正しい形式の盤面(initial_board)を用意する。
        Act:
            _validate_board を実行する。
        Assert:
            - 例外が発生しないこと。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act & Assert
        env._validate_board(board)  # 例外が発生しないことを確認

    @pytest.mark.parametrize(
        "invalid_board, expected_msg",
        [
            ("not_a_list", r"盤面は要素数8のリストである必要があります。"),
            ([[0] * 8] * 7, r"盤面は要素数8のリストである必要があります。"),
            (
                [[0] * 8] * 7 + [[0] * 7],
                r"盤面の各行は要素数8のリストである必要があります。",
            ),
            (
                [[0] * 8] * 7 + [[0, 0, 0, 0, 0, 0, 0, 2]],
                r"不正な盤面データが含まれています: 2",
            ),
        ],
    )
    def test_invalid_board(
        self, env: OthelloEnv, invalid_board: Any, expected_msg: str
    ) -> None:
        """
        [異常系] 不正な盤面データがValueErrorを送出すること。

        Arrange:
            リスト以外の型やサイズ違い、不正な値を含む盤面データを用意する。
        Act:
            _validate_board を実行する。
        Assert:
            - ValueErrorが発生し、適切なメッセージが含まれていること。
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match=expected_msg):
            env._validate_board(invalid_board)


class TestGetFlippableDiscs:
    """_get_flippable_discsメソッドのテストスイート"""

    def test_flippable_discs_initial(
        self, env: OthelloEnv, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 初期盤面で黒が合法手に置いたときに裏返せる石が取得できること。

        Arrange:
            初期盤面を用意する。
        Act:
            黒番で (2, 3) の座標に対して _get_flippable_discs を実行する。
        Assert:
            - 1つの石 (3, 3) が裏返せる座標として取得できること。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act
        flippable = env._get_flippable_discs(board, OthelloEnv.PLAYER_BLACK, 2, 3)

        # Assert
        assert len(flippable) == 1
        assert (3, 3) in flippable

    def test_flippable_discs_mid_game(
        self, env: OthelloEnv, mid_game_board: List[List[int]]
    ) -> None:
        """
        [正常系] 複雑な盤面で複数方向の裏返せる石が取得できること。

        Arrange:
            複数方向が裏返る mid_game_board を用意する。
        Act:
            黒番で (3, 2) の座標に対して _get_flippable_discs を実行する。
        Assert:
            - 横方向と斜め方向の計3つの石が裏返せる座標として取得できること。
        """
        # Arrange
        board = copy.deepcopy(mid_game_board)

        # Act
        flippable = env._get_flippable_discs(board, OthelloEnv.PLAYER_BLACK, 3, 2)

        # Assert
        assert len(flippable) == 3
        assert (3, 3) in flippable
        assert (3, 4) in flippable
        assert (4, 3) in flippable

    def test_flippable_discs_all_directions(
        self, env: OthelloEnv, star_board: List[List[int]]
    ) -> None:
        """
        [正常系] 星型盤面で全8方向の裏返せる石が正しく取得できること。

        Arrange:
            全8方向の裏返しが発生する star_board を用意する。
        Act:
            黒番で中央 (3, 3) に対して _get_flippable_discs を実行する。
        Assert:
            - 周囲8方向すべての石の座標が取得できること。
        """
        # Arrange
        board = copy.deepcopy(star_board)

        # Act
        flippable = env._get_flippable_discs(board, OthelloEnv.PLAYER_BLACK, 3, 3)

        # Assert
        assert len(flippable) == 8
        expected = [(2, 2), (2, 3), (2, 4), (3, 2), (3, 4), (4, 2), (4, 3), (4, 4)]
        for r, c in expected:
            assert (r, c) in flippable

    def test_flippable_discs_edge_no_flip(
        self, env: OthelloEnv, edge_board: List[List[int]]
    ) -> None:
        """
        [異常系（エッジケース）] 相手の石が連続して壁に到達した場合、裏返せないこと。

        Arrange:
            壁際に関する edge_board を用意する。
        Act:
            黒番で (0, 0) に対して _get_flippable_discs を実行する。
        Assert:
            - 自分の石で挟めていないため、裏返せる石として空のリストが返却されること。
        """
        # Arrange
        board = copy.deepcopy(edge_board)

        # Act
        flippable = env._get_flippable_discs(board, OthelloEnv.PLAYER_BLACK, 0, 0)

        # Assert
        assert flippable == []

    def test_flippable_discs_edge_flip(
        self, env: OthelloEnv, edge_board: List[List[int]]
    ) -> None:
        """
        [正常系] 壁際に自分の石がある場合、壁までの石が正しく裏返せること。

        Arrange:
            壁際に自分の石がある edge_board を用意する。
        Act:
            黒番で (7, 7) に対して _get_flippable_discs を実行する。
        Assert:
            - 壁の間にあるすべての相手の石の座標が取得できること。
        """
        # Arrange
        board = copy.deepcopy(edge_board)

        # Act
        flippable = env._get_flippable_discs(board, OthelloEnv.PLAYER_BLACK, 7, 7)

        # Assert
        assert len(flippable) == 6
        for c in range(1, 7):
            assert (7, c) in flippable

    @pytest.mark.parametrize(
        "player, row, col",
        [
            (OthelloEnv.PLAYER_BLACK, -1, 3),  # 盤面外(行が負)
            (OthelloEnv.PLAYER_BLACK, 8, 3),  # 盤面外(行が8以上)
            (OthelloEnv.PLAYER_BLACK, 2, -1),  # 盤面外(列が負)
            (OthelloEnv.PLAYER_BLACK, 2, 8),  # 盤面外(列が8以上)
            (OthelloEnv.PLAYER_BLACK, 3, 3),  # 既に石がある
            (99, 2, 3),  # 不正なプレイヤー
        ],
    )
    def test_no_flippable_discs_invalid_input(
        self,
        env: OthelloEnv,
        initial_board: List[List[int]],
        player: int,
        row: int,
        col: int,
    ) -> None:
        """
        [異常系] 無効な入力の場合、空のリストが返却されること。

        Arrange:
            盤面外の座標や、既に石がある座標を指定する。
        Act:
            _get_flippable_discs を実行する。
        Assert:
            - 裏返せる石なし（空のリスト）が返却されること。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act
        flippable = env._get_flippable_discs(board, player, row, col)

        # Assert
        assert flippable == []


class TestIsValidMove:
    """is_valid_moveメソッドのテストスイート"""

    @pytest.mark.parametrize(
        "player, row, col, expected",
        [
            (OthelloEnv.PLAYER_BLACK, 2, 3, True),  # 合法手
            (OthelloEnv.PLAYER_BLACK, 0, 0, False),  # 非合法手（裏返せない）
            (OthelloEnv.PLAYER_BLACK, 3, 3, False),  # すでに石がある
        ],
    )
    def test_is_valid_move(
        self,
        env: OthelloEnv,
        initial_board: List[List[int]],
        player: int,
        row: int,
        col: int,
        expected: bool,
    ) -> None:
        """
        [正常系・異常系] 合法手かどうかが正しく判定されること。

        Arrange:
            初期盤面と、いくつかの座標（合法手、裏返せない場所、石がある場所）を用意する。
        Act:
            is_valid_move を実行する。
        Assert:
            - 期待される判定結果 (True/False) が返却されること。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act
        result = env.is_valid_move(board, player, row, col)

        # Assert
        assert result is expected

    def test_is_valid_move_invalid_board(self, env: OthelloEnv) -> None:
        """
        [異常系] 不正な盤面の場合、例外が捕捉されてFalseが返ること。

        Arrange:
            文字列などの不正な型の盤面を用意する。
        Act:
            is_valid_move を実行する。
        Assert:
            - ValueErrorが捕捉され、安全に False が返却されること。
        """
        # Arrange & Act & Assert
        assert not env.is_valid_move("invalid_board", OthelloEnv.PLAYER_BLACK, 2, 3)  # type: ignore


class TestApplyMove:
    """apply_moveメソッドのテストスイート"""

    def test_apply_move_valid(
        self, env: OthelloEnv, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 合法手を打った場合、盤面が正しく更新されること。

        Arrange:
            初期盤面を用意し、元の盤面を変更しないか検証用にコピーしておく。
        Act:
            黒番で合法手 (2, 3) に対して apply_move を実行する。
        Assert:
            - 置いたマスと裏返ったマスの状態が PLAYER_BLACK になっていること。
            - 元の盤面オブジェクト (board) が破壊的に変更されていないこと。
        """
        # Arrange
        board = copy.deepcopy(initial_board)
        original_board = copy.deepcopy(board)

        # Act
        new_board = env.apply_move(board, OthelloEnv.PLAYER_BLACK, 2, 3)

        # Assert
        assert new_board[2][3] == OthelloEnv.PLAYER_BLACK
        assert new_board[3][3] == OthelloEnv.PLAYER_BLACK
        assert board == original_board

    @pytest.mark.parametrize(
        "row, col, expected_msg",
        [
            (-1, 0, r"座標\(-1, 0\)は盤面外です。"),
            (8, 0, r"座標\(8, 0\)は盤面外です。"),
            (3, 3, r"座標\(3, 3\)にはすでに石が置かれています。"),
            (0, 0, r"座標\(0, 0\)に石を置くことはできません。裏返せる石がありません。"),
        ],
    )
    def test_apply_move_invalid(
        self,
        env: OthelloEnv,
        initial_board: List[List[int]],
        row: int,
        col: int,
        expected_msg: str,
    ) -> None:
        """
        [異常系] 無効な手を打とうとした場合、ValueErrorが送出されること。

        Arrange:
            初期盤面と、無効な座標（盤面外、既に石がある、裏返せない）を用意する。
        Act:
            apply_move を実行する。
        Assert:
            - ValueErrorが発生し、適切なメッセージが含まれていること。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act & Assert
        with pytest.raises(ValueError, match=expected_msg):
            env.apply_move(board, OthelloEnv.PLAYER_BLACK, row, col)


class TestHasValidMoves:
    """has_valid_movesメソッドのテストスイート"""

    def test_has_valid_moves_true(
        self, env: OthelloEnv, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 合法手がある場合Trueが返ること。

        Arrange:
            両プレイヤーに合法手が存在する初期盤面を用意する。
        Act:
            各プレイヤーに対して has_valid_moves を実行する。
        Assert:
            - どちらのプレイヤーについても True が返却されること。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act
        result_black = env.has_valid_moves(board, OthelloEnv.PLAYER_BLACK)
        result_white = env.has_valid_moves(board, OthelloEnv.PLAYER_WHITE)

        # Assert
        assert result_black is True
        assert result_white is True

    def test_has_valid_moves_false(
        self, env: OthelloEnv, pass_board: List[List[int]]
    ) -> None:
        """
        [正常系] 合法手がない場合Falseが返ること。

        Arrange:
            白番に合法手が存在しない盤面 (pass_board) を用意する。
        Act:
            白番に対して has_valid_moves を実行する。
        Assert:
            - False が返却されること。
        """
        # Arrange
        board = copy.deepcopy(pass_board)

        # Act
        result_white = env.has_valid_moves(board, OthelloEnv.PLAYER_WHITE)

        # Assert
        assert result_white is False


class TestChangeTurn:
    """change_turnメソッドのテストスイート"""

    @pytest.mark.parametrize(
        "current, expected",
        [
            (OthelloEnv.PLAYER_BLACK, OthelloEnv.PLAYER_WHITE),
            (OthelloEnv.PLAYER_WHITE, OthelloEnv.PLAYER_BLACK),
        ],
    )
    def test_change_turn_valid(
        self, env: OthelloEnv, current: int, expected: int
    ) -> None:
        """
        [正常系] ターンが正しく切り替わること。

        Arrange:
            現在のプレイヤーの色を用意する。
        Act:
            change_turn を実行する。
        Assert:
            - もう一方のプレイヤーの色が返却されること。
        """
        # Arrange & Act
        next_turn = env.change_turn(current)

        # Assert
        assert next_turn == expected

    @pytest.mark.parametrize("invalid_player", [0, 2, -2, None])
    def test_change_turn_invalid(self, env: OthelloEnv, invalid_player: Any) -> None:
        """
        [異常系] 不正なプレイヤーが渡された場合ValueErrorが送出されること。

        Arrange:
            無効なプレイヤー値(0, 2, Noneなど)を用意する。
        Act:
            change_turn を実行する。
        Assert:
            - ValueErrorが発生し、適切なメッセージが含まれていること。
        """
        # Arrange & Act & Assert
        with pytest.raises(
            ValueError, match=f"不正なプレイヤー値です: {invalid_player}"
        ):
            env.change_turn(invalid_player)


class TestCalculateWinner:
    """calculate_winnerメソッドのテストスイート"""

    def test_calculate_winner_initial(
        self, env: OthelloEnv, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 初期状態の勝敗判定が正しく行われること（引き分け扱い）。

        Arrange:
            黒・白ともに同数(2個ずつ)の初期盤面を用意する。
        Act:
            calculate_winner を実行する。
        Assert:
            - 石の数が各2個で、勝者が EMPTY (引き分け) になっていること。
        """
        # Arrange
        board = copy.deepcopy(initial_board)

        # Act
        result = env.calculate_winner(board)

        # Assert
        assert result == {"black": 2, "white": 2, "winner": OthelloEnv.EMPTY}

    def test_calculate_winner_full_board(
        self, env: OthelloEnv, full_board: List[List[int]]
    ) -> None:
        """
        [正常系] 決着がついた状態の勝敗判定が正しく行われること。

        Arrange:
            黒が多く白が少ない決着盤面 (full_board) を用意する。
        Act:
            calculate_winner を実行する。
        Assert:
            - 黒石、白石の数が正しくカウントされ、勝者が PLAYER_BLACK であること。
        """
        # Arrange
        board = copy.deepcopy(full_board)

        # Act
        result = env.calculate_winner(board)

        # Assert
        assert result == {"black": 62, "white": 2, "winner": OthelloEnv.PLAYER_BLACK}

    def test_calculate_winner_white_win(self, env: OthelloEnv) -> None:
        """
        [正常系] 白が勝利するパターンの勝敗判定が正しく行われること。

        Arrange:
            白石が多く黒石が少ない盤面を用意する。
        Act:
            calculate_winner を実行する。
        Assert:
            - 白石の数が多く、勝者が PLAYER_WHITE であること。
        """
        # Arrange
        board = [[-1] * 8 for _ in range(8)]
        board[0][0] = 1

        # Act
        result = env.calculate_winner(board)

        # Assert
        assert result == {"black": 1, "white": 63, "winner": OthelloEnv.PLAYER_WHITE}
