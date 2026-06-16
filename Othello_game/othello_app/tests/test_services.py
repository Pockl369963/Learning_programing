import pytest
from django.contrib.auth.models import User
from othello_web.models import GameSession, MatchHistory
from othello_web.services import start_game, handle_abandoned_game, save_match_history

# ==========================================
# Fixtures
# ==========================================


@pytest.fixture
def test_user():
    """テスト用のダミーユーザーをセットアップ"""
    return User.objects.create_user(username="test_player", password="test_password")


@pytest.fixture
def initial_board():
    """テスト用の初期盤面 (必須フィールド回避用)"""
    board = [[0] * 8 for _ in range(8)]
    board[3][3], board[4][4] = -1, -1
    board[3][4], board[4][3] = 1, 1
    return board


# ==========================================
# Tests
# ==========================================


@pytest.mark.django_db
class TestOthelloServices:
    # --- 1. ゲーム開始とコイントス (start_game) ---

    def test_start_game_user_is_black(self, test_user, mocker):
        """
        [正常系] ゲーム開始時、ランダムでユーザーが先手(黒: 1)に決定されるケース
        """
        # Arrange
        # services.py 内で import されている random.choice をモックして先手を固定
        mocker.patch("othello_web.services.random.choice", return_value=1)
        opponent_type = "ai"

        # Act
        session = start_game(user=test_user, opponent=opponent_type)

        # Assert
        assert session.user == test_user
        assert session.opponent_type == opponent_type
        assert session.status == "playing"
        assert session.user_color == 1  # 黒(先手)

    def test_start_game_user_is_white(self, test_user, mocker):
        """
        [正常系] ゲーム開始時、ランダムでユーザーが後手(白: -1)に決定されるケース
        """
        # Arrange
        mocker.patch("othello_web.services.random.choice", return_value=-1)
        opponent_type = "random"

        # Act
        session = start_game(user=test_user, opponent=opponent_type)

        # Assert
        assert session.user == test_user
        assert session.opponent_type == opponent_type
        assert session.status == "playing"
        assert session.user_color == -1  # 白(後手)

    # --- 2. 途中離脱の検知と敗北記録 (handle_abandoned_game) ---

    def test_handle_abandoned_game_success(self, test_user, initial_board):
        """
        [正常系] 進行中のゲームが abandoned になり、敗北として MatchHistory に記録されるケース
        """
        # Arrange
        active_session = GameSession.objects.create(
            user=test_user,
            opponent_type="ai",
            status="playing",
            user_color=1,
            current_board=initial_board,
            current_turn=1,
        )

        finished_session = GameSession.objects.create(
            user=test_user,
            opponent_type="random",
            status="finished",
            user_color=-1,
            current_board=initial_board,
            current_turn=1,
        )

        # Act
        handle_abandoned_game(user=test_user)

        # Assert
        active_session.refresh_from_db()
        assert active_session.status == "abandoned"

        # 履歴に敗北(loss)が連動して作成されていること
        history = (
            MatchHistory.objects.filter(user=test_user, opponent_type="ai")
            .order_by("-played_at")
            .first()
        )
        assert history is not None
        assert history.result == "loss"

        # すでに完了しているセッションには影響がないこと
        finished_session.refresh_from_db()
        assert finished_session.status == "finished"

    def test_handle_abandoned_game_no_active_game(self, test_user):
        """
        [異常系] 進行中のゲームがない場合、ステータス変更や履歴作成が行われないこと
        """
        # Arrange
        initial_history_count = MatchHistory.objects.count()

        # Act
        handle_abandoned_game(user=test_user)

        # Assert
        assert MatchHistory.objects.count() == initial_history_count

    # --- 3. 最新10件の履歴保持トランザクション (save_match_history) ---

    def test_save_match_history_exactly_ten_records(self, test_user, initial_board):
        """
        [エッジケース] 履歴がちょうど10件になる場合、古い履歴の削除が発生しないこと
        """
        # Arrange: 既存の履歴を9件作成
        for _ in range(9):
            MatchHistory.objects.create(
                user=test_user, opponent_type="ai", result="win"
            )

        new_session = GameSession.objects.create(
            user=test_user,
            opponent_type="ai",
            status="finished",
            user_color=1,
            current_board=initial_board,
            current_turn=1,
        )

        # Act
        save_match_history(user=test_user, session=new_session, result="loss")

        # Assert
        assert MatchHistory.objects.filter(user=test_user).count() == 10

    def test_save_match_history_exceeds_ten_records(self, test_user, initial_board):
        """
        [エッジケース] 履歴が11件目として追加される場合、アトミックに最古の1件が削除され最新10件に保たれること
        """
        # Arrange: 既存の履歴を10件作成
        histories = []
        for _ in range(10):
            history = MatchHistory.objects.create(
                user=test_user, opponent_type="random", result="win"
            )
            histories.append(history)

        oldest_history_id = histories[0].id

        new_session = GameSession.objects.create(
            user=test_user,
            opponent_type="ai",
            status="finished",
            user_color=1,
            current_board=initial_board,
            current_turn=1,
        )

        # Act
        save_match_history(user=test_user, session=new_session, result="draw")

        # Assert
        assert MatchHistory.objects.filter(user=test_user).count() == 10

        # 最古の履歴が物理削除されていること
        assert not MatchHistory.objects.filter(id=oldest_history_id).exists()

        # 最新の履歴が追加されていること
        assert MatchHistory.objects.filter(
            user=test_user, opponent_type=new_session.opponent_type, result="draw"
        ).exists()
