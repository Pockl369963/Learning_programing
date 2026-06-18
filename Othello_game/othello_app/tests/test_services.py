"""
Tests for Othello web services.
"""

import pytest
from typing import List, Optional
from pytest_mock import MockerFixture

from django.contrib.auth.models import User
from othello_web.models import GameSession, MatchHistory
from othello_web.services import (
    start_game,
    handle_abandoned_game,
    save_match_history,
    surrender_game,
    process_timeout_abandoned_games,
    process_move,
    TurnConflictError,
    InvalidMoveError,
)
from model.othello_env import OthelloEnv, PLAYER_BLACK, PLAYER_WHITE


@pytest.fixture
def test_user() -> User:
    """テスト用のダミーユーザーを作成します。

    Returns:
        User: 作成されたテストユーザー
    """
    return User.objects.create_user(username="test_player", password="test_password")  # nosec B106


@pytest.fixture
def initial_board() -> List[List[int]]:
    """テスト用の初期盤面を生成します。

    Returns:
        List[List[int]]: 8x8の初期盤面リスト
    """
    return OthelloEnv().get_initial_board()


@pytest.mark.django_db
class TestOthelloServices:
    """Othelloサービスのビジネスロジックをテストするクラス。"""

    # -------------------------------------------------------------------------
    # 1. start_game
    # -------------------------------------------------------------------------

    def test_start_game_black(self, test_user: User, mocker: MockerFixture) -> None:
        """
        [正常系] ゲーム開始時、ランダム選択でユーザーが先手(黒)になる場合を検証する。

        Arrange:
            random.choice をモックし、必ず PLAYER_BLACK が選ばれるようにする。
        Act:
            start_game を実行し、新しいセッションを作成する。
        Assert:
            - 返されたセッションが指定したユーザーと対戦相手を持っていること。
            - ステータスが PLAYING であること。
            - ユーザーの色が PLAYER_BLACK であること。
        """
        # Arrange
        mocker.patch("othello_web.services.random.choice", return_value=PLAYER_BLACK)

        # Act
        session: GameSession = start_game(
            user=test_user, opponent=GameSession.OpponentType.AI
        )

        # Assert
        assert session.user == test_user
        assert session.opponent_type == GameSession.OpponentType.AI
        assert session.status == GameSession.Status.PLAYING
        assert session.user_color == PLAYER_BLACK

    def test_start_game_white(self, test_user: User, mocker: MockerFixture) -> None:
        """
        [正常系] ゲーム開始時、ランダム選択でユーザーが後手(白)になる場合を検証する。

        Arrange:
            random.choice をモックし、必ず PLAYER_WHITE が選ばれるようにする。
        Act:
            start_game を実行し、新しいセッションを作成する。
        Assert:
            - 返されたセッションのステータスが PLAYING であること。
            - ユーザーの色が PLAYER_WHITE になっていること。
        """
        # Arrange
        mocker.patch("othello_web.services.random.choice", return_value=PLAYER_WHITE)

        # Act
        session: GameSession = start_game(
            user=test_user, opponent=GameSession.OpponentType.RANDOM
        )

        # Assert
        assert session.user == test_user
        assert session.opponent_type == GameSession.OpponentType.RANDOM
        assert session.status == GameSession.Status.PLAYING
        assert session.user_color == PLAYER_WHITE

    # -------------------------------------------------------------------------
    # 2. handle_abandoned_game
    # -------------------------------------------------------------------------

    def test_handle_abandoned_game_success(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 進行中のゲームがある場合、ステータスがabandonedになり敗北履歴が保存されること。

        Arrange:
            進行中(PLAYING)の GameSession を事前に作成しておく。
        Act:
            handle_abandoned_game を実行する。
        Assert:
            - セッションのステータスが ABANDONED に更新されていること。
            - ユーザーに LOSS (敗北) の MatchHistory レコードが追加されていること。
        """
        # Arrange
        active_session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )

        # Act
        handle_abandoned_game(user=test_user)

        # Assert
        active_session.refresh_from_db()
        assert active_session.status == GameSession.Status.ABANDONED

        history: Optional[MatchHistory] = (
            MatchHistory.objects.filter(user=test_user).order_by("-played_at").first()
        )
        assert history is not None
        assert history.result == MatchHistory.Result.LOSS
        assert history.opponent_type == GameSession.OpponentType.AI

    def test_handle_abandoned_game_no_active(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [異常系] 進行中のゲームがない場合、何も変更されずエラーも起きないこと。

        Arrange:
            すでに終了した(FINISHED) GameSession のみを作成しておく。
            実行前の履歴件数を記録する。
        Act:
            handle_abandoned_game を実行する。
        Assert:
            - エラーが発生しないこと。
            - MatchHistoryの件数が実行前と変わっていないこと。
        """
        # Arrange
        GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.FINISHED,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        initial_history_count: int = MatchHistory.objects.count()

        # Act
        handle_abandoned_game(user=test_user)

        # Assert
        assert MatchHistory.objects.count() == initial_history_count

    # -------------------------------------------------------------------------
    # 3. save_match_history
    # -------------------------------------------------------------------------

    def test_save_match_history_ninth_record(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] すでに9件(上限未満)の履歴がある状態で1件追加し、合計10件になること。

        Arrange:
            上限数(MAX_MATCH_HISTORY) - 1 件の MatchHistory と、終了済みのセッションを作成する。
        Act:
            save_match_history を実行して新しい結果を追加する。
        Assert:
            - ユーザーの MatchHistory が上限数に等しくなっていること。
        """
        # Arrange
        for _ in range(MatchHistory.MAX_MATCH_HISTORY - 1):
            MatchHistory.objects.create(
                user=test_user,
                opponent_type=GameSession.OpponentType.AI,
                result=MatchHistory.Result.WIN,
            )

        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.FINISHED,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )

        # Act
        save_match_history(
            user=test_user, session=session, result=MatchHistory.Result.WIN
        )

        # Assert
        assert (
            MatchHistory.objects.filter(user=test_user).count()
            == MatchHistory.MAX_MATCH_HISTORY
        )

    def test_save_match_history_eleventh_record(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] すでに10件(上限)の履歴がある状態で1件追加した場合、最古のレコードが削除され、合計10件が維持されること。

        Arrange:
            上限数(MAX_MATCH_HISTORY)の MatchHistory を作成し、最古のレコードのIDを記録する。
        Act:
            save_match_history を実行して新たな結果を追加する。
        Assert:
            - MatchHistory の全体数が上限数に維持されていること。
            - 記録しておいた最古のレコードがDBから削除されていること。
            - 最新のレコードが新たに追加されたものであること。
        """
        # Arrange
        histories: List[MatchHistory] = []
        for _ in range(MatchHistory.MAX_MATCH_HISTORY):
            history = MatchHistory.objects.create(
                user=test_user,
                opponent_type=GameSession.OpponentType.AI,
                result=MatchHistory.Result.WIN,
            )
            histories.append(history)

        oldest_history_id = histories[0].id

        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.RANDOM,
            status=GameSession.Status.FINISHED,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )

        # Act
        save_match_history(
            user=test_user, session=session, result=MatchHistory.Result.LOSS
        )

        # Assert
        assert (
            MatchHistory.objects.filter(user=test_user).count()
            == MatchHistory.MAX_MATCH_HISTORY
        )

        # 最古のレコードが削除されたことを確認
        assert not MatchHistory.objects.filter(id=oldest_history_id).exists()

        # 最新のレコードが追加されたことを確認
        latest_history: Optional[MatchHistory] = (
            MatchHistory.objects.filter(user=test_user)
            .order_by("-played_at", "-pk")
            .first()
        )
        assert latest_history is not None
        assert latest_history.opponent_type == GameSession.OpponentType.RANDOM
        assert latest_history.result == MatchHistory.Result.LOSS

    # -------------------------------------------------------------------------
    # 4. surrender_game
    # -------------------------------------------------------------------------

    def test_surrender_game_success(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 自分の進行中のゲームをサレンダー（投了）できること。

        Arrange:
            PLAYING状態の GameSession を作成する。
        Act:
            surrender_game を実行する。
        Assert:
            - セッションステータスが FINISHED になること。
            - 敗北(LOSS)履歴が新しく保存されること。
        """
        # Arrange
        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )

        # Act
        surrender_game(user=test_user, session_id=session.id)

        # Assert
        session.refresh_from_db()
        assert session.status == GameSession.Status.FINISHED

        history: Optional[MatchHistory] = (
            MatchHistory.objects.filter(user=test_user).order_by("-played_at").first()
        )
        assert history is not None
        assert history.result == MatchHistory.Result.LOSS

    def test_surrender_game_invalid_state(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [異常系] すでに終了したゲームをサレンダーしようとするとValueErrorが発生すること。

        Arrange:
            すでに終了(FINISHED)状態の GameSession を作成する。
        Act:
            surrender_game を実行する。
        Assert:
            - ValueErrorが発生し、適切なメッセージが含まれていること。
        """
        # Arrange
        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.FINISHED,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="サレンダーできるのは進行中のゲームのみです"
        ):
            surrender_game(user=test_user, session_id=session.id)

    def test_surrender_game_unauthorized(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [異常系] 他人のゲームセッションをサレンダーしようとした場合、エラーが発生すること。

        Arrange:
            他ユーザーに紐づく PLAYING状態の GameSession を作成する。
        Act:
            対象セッションに対して自分(test_user)が surrender_game を実行する。
        Assert:
            - セッション取得に失敗し、例外(DoesNotExist等)が発生すること。
        """
        # Arrange
        other_user = User.objects.create_user(
            username="other_user", password="password"
        )  # nosec B106
        session: GameSession = GameSession.objects.create(
            user=other_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )

        # Act & Assert
        with pytest.raises(Exception):
            surrender_game(user=test_user, session_id=session.id)

    # -------------------------------------------------------------------------
    # 5. process_timeout_abandoned_games
    # -------------------------------------------------------------------------

    def test_process_timeout_abandoned_games(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 1時間以上操作がないPLAYING状態のゲームをABANDONEDに変更し、LOSS履歴を作成すること。

        Arrange:
            2時間前に更新されたPLAYING状態のセッションと、30分前に更新されたセッションを作成する。
        Act:
            process_timeout_abandoned_games を実行する。
        Assert:
            - 処理件数として 1 が返ること。
            - 2時間前のセッションは ABANDONED になり、LOSS履歴が作成されていること。
            - 30分前のセッションは PLAYING のままであること。
        """
        from datetime import timedelta
        from django.utils import timezone

        # Arrange
        # タイムアウト対象 (2時間前に更新)
        session_timeout = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        old_time = timezone.now() - timedelta(hours=2)
        GameSession.objects.filter(id=session_timeout.id).update(updated_at=old_time)

        # タイムアウト対象外 (30分前に更新)
        session_active = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        recent_time = timezone.now() - timedelta(minutes=30)
        GameSession.objects.filter(id=session_active.id).update(updated_at=recent_time)

        # Act
        processed_count = process_timeout_abandoned_games()

        # Assert
        assert processed_count == 1

        session_timeout.refresh_from_db()
        assert session_timeout.status == GameSession.Status.ABANDONED

        session_active.refresh_from_db()
        assert session_active.status == GameSession.Status.PLAYING

        history: Optional[MatchHistory] = MatchHistory.objects.filter(
            user=test_user
        ).first()
        assert history is not None
        assert history.result == MatchHistory.Result.LOSS

    def test_process_timeout_abandoned_games_exclude_finished(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] すでにFINISHEDやABANDONEDになっている古いゲームはタイムアウトの処理対象外となること。

        Arrange:
            2時間前に更新されたが、ステータスは FINISHED であるセッションを作成する。
        Act:
            process_timeout_abandoned_games を実行する。
        Assert:
            - 処理件数として 0 が返ること。
            - セッションステータスが FINISHED のままであること。
            - 余計な MatchHistory が作成されていないこと。
        """
        from datetime import timedelta
        from django.utils import timezone

        # Arrange
        # 1時間以上前に更新されたが、すでに終了（FINISHED）しているゲーム
        session_finished = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.FINISHED,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        old_time = timezone.now() - timedelta(hours=2)
        GameSession.objects.filter(id=session_finished.id).update(updated_at=old_time)

        initial_history_count = MatchHistory.objects.count()

        # Act
        processed_count = process_timeout_abandoned_games()

        # Assert
        assert processed_count == 0

        session_finished.refresh_from_db()
        assert session_finished.status == GameSession.Status.FINISHED

        # 誤って新たな敗北履歴が作成されていないことを確認
        assert MatchHistory.objects.count() == initial_history_count

    # -------------------------------------------------------------------------
    # 6. process_move (Issue 3: 排他制御とバリデーション)
    # -------------------------------------------------------------------------

    def test_process_move_success(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [正常系] 自分のターンで正しい合法手を打った場合、盤面とターンが更新されること。

        Arrange:
            PLAYING状態で黒番の GameSession を作成し、合法手(2, 3)を用意する。
        Act:
            process_move を実行する。
        Assert:
            - セッションの盤面の (2, 3) が PLAYER_BLACK に書き換わっていること。
            - 次のターンが PLAYER_WHITE に変更されていること。
        """
        # Arrange
        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        # 黒の初期合法手の一つ (2, 3)
        row, col = 2, 3

        # Act
        process_move(
            user=test_user,
            session_id=session.id,
            row=row,
            col=col,
            expected_turn=PLAYER_BLACK,
        )

        # Assert
        session.refresh_from_db()
        assert session.current_board[row][col] == PLAYER_BLACK
        assert session.current_turn == PLAYER_WHITE

    def test_process_move_turn_conflict(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [異常系(排他制御)] 期待するターンと実際のターンが異なる場合、TurnConflictError(409相当)が発生すること。

        Arrange:
            現在のターンがPLAYER_BLACKである GameSession を作成する。
            期待するターンとして PLAYER_WHITE を指定する。
        Act:
            process_move を実行する。
        Assert:
            - TurnConflictError が発生すること。
        """
        # Arrange
        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        row, col = 2, 3

        # Act & Assert
        # 連打などで過去のターン(白)の状態でリクエストが来たケース
        with pytest.raises(TurnConflictError):
            process_move(
                user=test_user,
                session_id=session.id,
                row=row,
                col=col,
                expected_turn=PLAYER_WHITE,  # 実際のターン(PLAYER_BLACK)と不一致
            )

    def test_process_move_invalid_move(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        [異常系(バリデーション)] 不正な座標に置こうとした場合、InvalidMoveError(400相当)が発生すること。

        Arrange:
            初期盤面の GameSession を作成し、合法手ではない座標 (0, 0) を用意する。
        Act:
            process_move を実行する。
        Assert:
            - InvalidMoveError が発生すること。
        """
        # Arrange
        session: GameSession = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=PLAYER_BLACK,
            current_board=initial_board,
            current_turn=PLAYER_BLACK,
        )
        # (0, 0) は初期盤面では合法手ではない
        row, col = 0, 0

        # Act & Assert
        with pytest.raises(InvalidMoveError):
            process_move(
                user=test_user,
                session_id=session.id,
                row=row,
                col=col,
                expected_turn=PLAYER_BLACK,
            )
