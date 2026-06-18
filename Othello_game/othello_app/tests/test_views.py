import json
import pytest
import uuid
from unittest.mock import patch
from typing import Any, Dict, List
from django.contrib.auth.models import User
from django.test import Client

from othello_web.models import GameSession, MatchHistory
from model.othello_env import OthelloEnv


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def client() -> Client:
    """標準のDjangoテストクライアント"""
    return Client()


@pytest.fixture
def test_user() -> User:
    """テスト用の有効なユーザーオブジェクト"""
    return User.objects.create_user(username="testuser", password="testpassword123")  # nosec B106


@pytest.fixture
def logged_in_client(client: Client, test_user: User) -> Client:
    """認証済みのDjangoテストクライアント"""
    client.login(username="testuser", password="testpassword123")
    return client


@pytest.fixture
def active_session(test_user: User) -> GameSession:
    """テストユーザーに紐づく、プレイ中のゲームセッション (ユーザーが黒番)"""
    env = OthelloEnv()
    return GameSession.objects.create(
        user=test_user,
        opponent_type=GameSession.OpponentType.AI,
        status=GameSession.Status.PLAYING,
        user_color=GameSession.Color.BLACK,
        current_board=env.get_initial_board(),
        current_turn=GameSession.Color.BLACK,
    )


# ====================================================================
# API View Tests
# ====================================================================


@pytest.mark.django_db
class TestGameStartView:
    """
    GameStartView (POST /api/game/start/) のテストクラス
    初期盤面の生成と新しいゲームセッションの開始を検証する。
    """

    def test_start_game_unauthenticated(self, client: Client) -> None:
        """
        [異常系] 未認証のユーザーがアクセスした場合の挙動を検証する。

        Arrange:
            未認証のテストクライアントを用意する。
        Act:
            /api/game/start/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが403(Forbidden) もしくは 302(Redirect) であること。
        """
        # Arrange
        url = "/api/game/start/"
        payload: Dict[str, str] = {"opponent": "ai"}

        # Act
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code in [302, 403]

    def test_start_game_invalid_payload(self, logged_in_client: Client) -> None:
        """
        [異常系] 必須パラメータが欠損している、または不正な形式の場合の挙動を検証する。

        Arrange:
            認証済みのテストクライアントを用意し、不正なペイロード（空、または無効なopponent）を作成する。
        Act:
            /api/game/start/ にPOSTリクエストを送信する。
        Assert:
            - いずれのリクエストでも HTTPステータスコードが400(Bad Request) であること。
        """
        # Arrange
        url = "/api/game/start/"

        # Act (ペイロード空)
        response1 = logged_in_client.post(
            url, json.dumps({}), content_type="application/json"
        )
        # Assert
        assert response1.status_code == 400

        # Act (不正な値)
        response2 = logged_in_client.post(
            url, json.dumps({"opponent": "alien"}), content_type="application/json"
        )
        # Assert
        assert response2.status_code == 400

    @patch("othello_web.services.random.choice")
    def test_start_game_success_user_first(
        self, mock_choice: Any, logged_in_client: Client, test_user: User
    ) -> None:
        """
        [正常系] コイントスでユーザーが先手(黒)になった場合の挙動を検証する。

        Arrange:
            random.choice をモックし、必ずユーザーがBLACKになるよう固定する。
        Act:
            /api/game/start/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが200 OKであること。
            - ユーザーの色と現在のターンが共にBLACKであること。
            - 盤面の石の数が初期状態のまま(4つ)であること。
        """
        # Arrange
        mock_choice.return_value = GameSession.Color.BLACK
        url = "/api/game/start/"

        # Act
        response = logged_in_client.post(
            url, json.dumps({"opponent": "ai"}), content_type="application/json"
        )

        # Assert
        assert response.status_code == 200

        data: Dict[str, Any] = response.json()
        assert data["user_color"] == GameSession.Color.BLACK
        assert data["current_turn"] == GameSession.Color.BLACK

        board = data["current_board"]
        stone_count = sum(1 for row in board for cell in row if cell != 0)
        assert stone_count == 4

    @patch("othello_web.services.random.choice")
    def test_start_game_success_ai_first(
        self, mock_choice: Any, logged_in_client: Client, test_user: User
    ) -> None:
        """
        [正常系] コイントスでAIが先手(黒)になった場合の挙動を検証する。

        Arrange:
            random.choice をモックし、必ずユーザーがWHITE(後手)になるよう固定する。
        Act:
            /api/game/start/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが200 OKであること。
            - レスポンスが返る前にAIの手番が処理されるため、ターンがユーザー(WHITE)に移っていること。
            - 盤面の石の数が5つ(初期4つ + AI初手1つ)に増えていること。
        """
        # Arrange
        mock_choice.return_value = GameSession.Color.WHITE
        url = "/api/game/start/"

        # Act
        response = logged_in_client.post(
            url, json.dumps({"opponent": "ai"}), content_type="application/json"
        )

        # Assert
        assert response.status_code == 200

        data: Dict[str, Any] = response.json()
        assert data["user_color"] == GameSession.Color.WHITE
        assert data["current_turn"] == GameSession.Color.WHITE

        board = data["current_board"]
        stone_count = sum(1 for row in board for cell in row if cell != 0)
        assert stone_count == 5


@pytest.mark.django_db
class TestGameMoveView:
    """
    GameMoveView (POST /api/game/move/) のテストクラス
    ユーザーの手番処理と、対AI戦におけるAIの手番処理、及び終了判定を検証する。
    """

    def test_move_unauthenticated(
        self, client: Client, active_session: GameSession
    ) -> None:
        """
        [異常系] 未認証のユーザーがアクセスした場合の挙動を検証する。

        Arrange:
            未認証のテストクライアントを用意する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが403 もしくは 302 であること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {
            "session_id": str(active_session.id),
            "row": 2,
            "col": 3,
            "expected_turn": 1,
        }

        # Act
        response = client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code in [302, 403]

    def test_move_missing_fields(
        self, logged_in_client: Client, active_session: GameSession
    ) -> None:
        """
        [異常系] リクエストペイロードに必要なパラメータが欠損している場合の挙動を検証する。

        Arrange:
            row, colなどの必須キーを含まないペイロードを作成する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが400(Bad Request)であること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {"session_id": str(active_session.id)}

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 400

    def test_move_not_found(self, logged_in_client: Client) -> None:
        """
        [異常系] DBに存在しないsession_idが指定された場合の挙動を検証する。

        Arrange:
            新しく生成したランダムなUUIDをsession_idとしてペイロードを作成する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - サーバーエラー(500)で落ちることなく、正しく404(Not Found)が返ること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {
            "session_id": str(uuid.uuid4()),
            "row": 2,
            "col": 3,
            "expected_turn": 1,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 404

    def test_move_invalid_uuid(self, logged_in_client: Client) -> None:
        """
        [異常系] UUID形式ではない不正なsession_idが指定された場合の挙動を検証する。

        Arrange:
            UUIDのフォーマットに反する文字列をsession_idとしたペイロードを作成する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - バリデーションに失敗し、400(Bad Request)が返ること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {
            "session_id": "invalid-uuid-string",
            "row": 2,
            "col": 3,
            "expected_turn": 1,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 400

    def test_move_turn_conflict(
        self, logged_in_client: Client, active_session: GameSession
    ) -> None:
        """
        [異常系] クライアントが期待するターンと実際のターンが不一致の場合の挙動を検証する。

        Arrange:
            現在のターンがBLACKのセッションに対し、expected_turn=WHITEでリクエストを送る。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが409(Conflict)であること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {
            "session_id": str(active_session.id),
            "row": 2,
            "col": 3,
            "expected_turn": GameSession.Color.WHITE,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 409

    def test_move_invalid_move(
        self, logged_in_client: Client, active_session: GameSession
    ) -> None:
        """
        [異常系] オセロのルール上置けないマスを指定した場合の挙動を検証する。

        Arrange:
            初期盤面において、合法手ではない(石を裏返せない)マス (row=0, col=0) を指定する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが400(Bad Request)であること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {
            "session_id": str(active_session.id),
            "row": 0,
            "col": 0,
            "expected_turn": GameSession.Color.BLACK,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 400

    def test_move_game_not_playing(
        self, logged_in_client: Client, test_user: User
    ) -> None:
        """
        [異常系] 既に終了(または放棄)したゲームに対して手を打とうとした場合の挙動を検証する。

        Arrange:
            statusがFINISHEDのゲームセッションを作成する。
        Act:
            そのセッションに対してPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが400(Bad Request)であること。
        """
        # Arrange
        session = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.FINISHED,
            user_color=GameSession.Color.BLACK,
            current_board=OthelloEnv().get_initial_board(),
            current_turn=GameSession.Color.BLACK,
        )
        url = "/api/game/move/"
        payload = {
            "session_id": str(session.id),
            "row": 2,
            "col": 3,
            "expected_turn": GameSession.Color.BLACK,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 400

    def test_move_malformed_json(self, logged_in_client: Client) -> None:
        """
        [異常系] 不正なJSON文字列がリクエストボディとして送信された場合の挙動を検証する。

        Arrange:
            パース不可能なJSON文字列を用意する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが400(Bad Request)であること。
        """
        # Arrange
        url = "/api/game/move/"
        invalid_json = '{"session_id": "123", "row": 2'  # 途中で切れている

        # Act
        response = logged_in_client.post(
            url, data=invalid_json, content_type="application/json"
        )

        # Assert
        assert response.status_code == 400

    def test_move_success(
        self, logged_in_client: Client, active_session: GameSession
    ) -> None:
        """
        [正常系] ユーザーが正しい手を打ち、AIも手を返す一連の流れを検証する。

        Arrange:
            初期盤面において、合法手である (row=2, col=3) を指定する。
        Act:
            /api/game/move/ にPOSTリクエストを送信する。
        Assert:
            - HTTPステータスコードが200 OKであること。
            - ユーザー(黒) -> AI(白) と手番が進み、最終的に現在のターンが黒に戻っていること。
            - セッションステータスが引き続きPLAYINGであること。
        """
        # Arrange
        url = "/api/game/move/"
        payload = {
            "session_id": str(active_session.id),
            "row": 2,
            "col": 3,
            "expected_turn": 1,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == GameSession.Status.PLAYING
        assert data["current_turn"] == GameSession.Color.BLACK

    def test_move_game_over(self, logged_in_client: Client, test_user: User) -> None:
        """
        [正常系] 手を打った結果、ゲームが終了する(盤面が埋まる等)シナリオを検証する。

        Arrange:
            残り1マスで終了となる擬似的な盤面を持ったセッションを作成する。
        Act:
            その最後のマス(row=0, col=1)に石を置くリクエストを送信する。
        Assert:
            - HTTPステータスコードが200 OKであること。
            - セッションステータスが FINISHED に更新されること。
            - ゲーム結果が MatchHistory に1件保存されていること。
        """
        # Arrange
        board: List[List[int]] = [[OthelloEnv.PLAYER_BLACK] * 8 for _ in range(8)]
        board[0][0] = OthelloEnv.PLAYER_BLACK
        board[0][1] = OthelloEnv.PLAYER_WHITE
        board[0][2] = OthelloEnv.EMPTY  # 最後の空きマス

        session = GameSession.objects.create(
            user=test_user,
            opponent_type=GameSession.OpponentType.AI,
            status=GameSession.Status.PLAYING,
            user_color=GameSession.Color.BLACK,
            current_board=board,
            current_turn=GameSession.Color.BLACK,
        )

        url = "/api/game/move/"
        payload = {
            "session_id": str(session.id),
            "row": 0,
            "col": 2,
            "expected_turn": GameSession.Color.BLACK,
        }

        # Act
        response = logged_in_client.post(
            url, json.dumps(payload), content_type="application/json"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == GameSession.Status.FINISHED
        assert MatchHistory.objects.filter(user=test_user).count() == 1


@pytest.mark.django_db
class TestUserHistoryView:
    """
    UserHistoryView (GET /api/user/history/) のテストクラス
    ユーザーの過去の対戦履歴を取得する処理を検証する。
    """

    def test_history_unauthenticated(self, client: Client) -> None:
        """
        [異常系] 未認証のユーザーがアクセスした場合の挙動を検証する。

        Arrange:
            未認証のテストクライアントを用意する。
        Act:
            /api/user/history/ にGETリクエストを送信する。
        Assert:
            - HTTPステータスコードが403 もしくは 302 であること。
        """
        # Arrange
        url = "/api/user/history/"

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code in [302, 403]

    def test_history_success_limit(
        self, logged_in_client: Client, test_user: User
    ) -> None:
        """
        [正常系] 履歴が大量にある場合でも、最新の10件のみが返されることを検証する。

        Arrange:
            15件のMatchHistoryレコードを作成する。
        Act:
            /api/user/history/ にGETリクエストを送信する。
        Assert:
            - HTTPステータスコードが200 OKであること。
            - 取得された履歴リストの長さが、10件に制限されていること。
        """
        # Arrange
        for i in range(15):
            MatchHistory.objects.create(
                user=test_user,
                opponent_type=GameSession.OpponentType.AI,
                result=MatchHistory.Result.WIN,
            )
        url = "/api/user/history/"

        # Act
        response = logged_in_client.get(url)

        # Assert
        assert response.status_code == 200
        data: Dict[str, Any] = response.json()
        history_list: List[Dict[str, Any]] = data["history"]

        assert len(history_list) == 10

    def test_history_empty(self, logged_in_client: Client) -> None:
        """
        [正常系] 履歴が1件も存在しない場合の挙動を検証する。

        Arrange:
            MatchHistoryレコードが1件も存在しない状態を作る。
        Act:
            /api/user/history/ にGETリクエストを送信する。
        Assert:
            - HTTPステータスコードが200 OKであること。
            - 取得された履歴リストが空のリストであること。
        """
        # Arrange
        url = "/api/user/history/"

        # Act
        response = logged_in_client.get(url)

        # Assert
        assert response.status_code == 200
        data: Dict[str, Any] = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
        assert len(data["history"]) == 0
