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
    MAX_MATCH_HISTORY,
)
from model.othello_env import get_initial_board, PLAYER_BLACK, PLAYER_WHITE


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
    return get_initial_board()


@pytest.mark.django_db
class TestOthelloServices:
    """Othelloサービスのビジネスロジックをテストするクラス。"""

    # -------------------------------------------------------------------------
    # 1. start_game
    # -------------------------------------------------------------------------

    def test_start_game_black(self, test_user: User, mocker: MockerFixture) -> None:
        """
        正常系: ゲーム開始時、ランダム選択でユーザーが先手(黒)になる場合。

        Args:
            test_user (User): テスト用ユーザー
            mocker (MockerFixture): pytest-mockのMockerFixture
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
        正常系: ゲーム開始時、ランダム選択でユーザーが後手(白)になる場合。

        Args:
            test_user (User): テスト用ユーザー
            mocker (MockerFixture): pytest-mockのMockerFixture
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
        正常系: 進行中のゲームがある場合、ステータスがabandonedになり敗北履歴が保存されること。

        Args:
            test_user (User): テスト用ユーザー
            initial_board (List[List[int]]): 初期盤面
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
        異常系: 進行中のゲームがない場合、何も変更されずエラーも起きないこと。

        Args:
            test_user (User): テスト用ユーザー
            initial_board (List[List[int]]): 初期盤面
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
        正常系: すでに9件の履歴がある状態で1件追加し、合計10件になること。

        Args:
            test_user (User): テスト用ユーザー
            initial_board (List[List[int]]): 初期盤面
        """
        # Arrange
        for _ in range(MAX_MATCH_HISTORY - 1):
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
        assert MatchHistory.objects.filter(user=test_user).count() == MAX_MATCH_HISTORY

    def test_save_match_history_eleventh_record(
        self, test_user: User, initial_board: List[List[int]]
    ) -> None:
        """
        境界値: すでに10件の履歴がある状態で1件追加した場合、最古のレコードが削除され、合計10件が維持されること。

        Args:
            test_user (User): テスト用ユーザー
            initial_board (List[List[int]]): 初期盤面
        """
        # Arrange
        histories: List[MatchHistory] = []
        for _ in range(MAX_MATCH_HISTORY):
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
        assert MatchHistory.objects.filter(user=test_user).count() == MAX_MATCH_HISTORY

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
