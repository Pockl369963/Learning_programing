import pytest
import uuid
from typing import List, Any
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from othello_web.models import GameSession, MatchHistory
from model.othello_env import OthelloEnv, PLAYER_BLACK

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def valid_user() -> User:
    """テスト用の有効なユーザーオブジェクトを提供するフィクスチャ"""
    return User.objects.create_user(username="testuser", password="testpassword123")  # nosec B106


@pytest.fixture
def initial_board() -> List[List[int]]:
    """オセロの初期状態（8x8）の盤面データを提供するフィクスチャ"""
    return OthelloEnv().get_initial_board()


# ====================================================================
# GameSession Model Tests
# ====================================================================


@pytest.mark.django_db
def test_gamesession_create_success(
    valid_user: User, initial_board: List[List[int]]
) -> None:
    """
    [正常系] 正しいパラメータでGameSessionが正常に作成・保存されること。
    UUIDの自動生成や、DateTimeFieldの自動設定(auto_now/add)も検証する。

    Arrange:
        GameSessionの各フィールドに対して、正常なデータを用意する。
    Act:
        session.full_clean() でバリデーションを実行し、session.save() で保存する。
    Assert:
        - UUIDが生成されていること
        - created_at, updated_atが自動でセットされていること
        - user, statusなどが期待した値であること
    """
    session = GameSession(
        user=valid_user,
        opponent_type=GameSession.OpponentType.AI,
        user_color=PLAYER_BLACK,
        current_board=initial_board,
        current_turn=PLAYER_BLACK,
        status=GameSession.Status.PLAYING,
    )
    session.full_clean()  # モデルレベルのバリデーションを実行
    session.save()

    assert isinstance(session.id, uuid.UUID)
    assert session.user == valid_user
    assert session.created_at is not None
    assert session.updated_at is not None
    assert session.status == GameSession.Status.PLAYING


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("opponent_type", "friend"),  # Choices定義外 ('ai', 'random' 以外)
        (
            "status",
            "invalid",
        ),  # Choices定義外 ('playing', 'finished', 'abandoned' 以外)
    ],
)
def test_gamesession_invalid_choices(
    valid_user: User, initial_board: List[List[int]], field: str, invalid_value: Any
) -> None:
    """
    [異常系] 定義外のChoices値が設定された場合、ValidationErrorが発生すること。

    Arrange:
        正常なデータセットを用意し、対象のChoiceフィールドに定義外の値(invalid_value)をセットする。
    Act:
        session.full_clean() でバリデーションを実行する。
    Assert:
        - ValidationErrorが発生すること。
        - エラーメッセージ内に該当フィールド名が含まれていること。
    """
    data: dict[str, Any] = {
        "user": valid_user,
        "opponent_type": GameSession.OpponentType.AI,
        "user_color": PLAYER_BLACK,
        "current_board": initial_board,
        "current_turn": PLAYER_BLACK,
        "status": GameSession.Status.PLAYING,
    }
    data[field] = invalid_value
    session = GameSession(**data)

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert field in excinfo.value.message_dict


@pytest.mark.django_db
def test_gamesession_null_constraints(initial_board: List[List[int]]) -> None:
    """
    [異常系] 必須フィールド(user)が欠落している場合、ValidationErrorが発生すること。

    Arrange:
        userフィールドを除いた状態でGameSessionを初期化する。
    Act:
        session.full_clean() でバリデーションを実行する。
    Assert:
        - ValidationErrorが発生すること。
        - エラーメッセージ内に 'user' 関連のメッセージが含まれていること。
    """
    session = GameSession(
        opponent_type=GameSession.OpponentType.AI,
        user_color=PLAYER_BLACK,
        current_board=initial_board,
        current_turn=PLAYER_BLACK,
        status=GameSession.Status.PLAYING,
    )

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert "user" in excinfo.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_val", [0, 2, -2, 100])
def test_gamesession_color_and_turn_boundary_validation(
    valid_user: User, initial_board: List[List[int]], invalid_val: int
) -> None:
    """
    [異常系] user_color および current_turn に対して、許容されない整数値を代入した際にバリデーションエラーになること。

    Arrange:
        user_color と current_turn にChoices定義外の整数値(invalid_val)をセットする。
    Act:
        session.full_clean() でバリデーションを実行する。
    Assert:
        - ValidationErrorが発生すること。
        - エラーメッセージ内に 'user_color' および 'current_turn' が含まれていること。
    """
    session = GameSession(
        user=valid_user,
        opponent_type=GameSession.OpponentType.AI,
        user_color=invalid_val,  # 許容されない値
        current_board=initial_board,
        current_turn=invalid_val,  # 許容されない値
        status=GameSession.Status.PLAYING,
    )

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert "user_color" in excinfo.value.message_dict
    assert "current_turn" in excinfo.value.message_dict


@pytest.mark.django_db
def test_gamesession_invalid_current_board_type(valid_user: User) -> None:
    """
    [異常系] current_board に対して不正な型(文字列など)を代入した場合、適切に弾かれること。

    Arrange:
        current_board に不正な型(文字列など)をセットしてGameSessionを初期化する。
    Act:
        session.full_clean() でカスタムバリデータを含めたバリデーションを実行する。
    Assert:
        - ValidationErrorが発生すること。
        - エラーメッセージ内に 'current_board' が含まれていること。
    """
    session = GameSession(
        user=valid_user,
        opponent_type=GameSession.OpponentType.AI,
        user_color=PLAYER_BLACK,
        current_board="This is not an 8x8 array",  # 不正なデータ型
        current_turn=PLAYER_BLACK,
        status=GameSession.Status.PLAYING,
    )

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert "current_board" in excinfo.value.message_dict


# ====================================================================
# MatchHistory Model Tests
# ====================================================================


@pytest.mark.django_db
def test_matchhistory_create_success(valid_user: User) -> None:
    """
    [正常系] 正しいパラメータでMatchHistoryが正常に作成・保存されること。

    Arrange:
        MatchHistoryに必要な正常なパラメータを用意する。
    Act:
        history.full_clean() でバリデーションを実行し、history.save() でDBに保存する。
    Assert:
        - idが生成されていること
        - user, played_at, resultが期待した値であること
    """
    history = MatchHistory(
        user=valid_user,
        opponent_type=GameSession.OpponentType.AI,
        result=MatchHistory.Result.WIN,
    )
    history.full_clean()
    history.save()

    assert history.id is not None
    assert history.user == valid_user
    assert history.played_at is not None
    assert history.result == MatchHistory.Result.WIN


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("opponent_type", "human"),  # 'ai', 'random' 以外
        ("result", "surrender"),  # 'win', 'loss', 'draw' 以外
    ],
)
def test_matchhistory_invalid_choices(
    valid_user: User, field: str, invalid_value: Any
) -> None:
    """
    [異常系] MatchHistoryにおける定義外のChoices値が設定された場合、ValidationErrorが発生すること。

    Arrange:
        正常なデータセットを用意し、対象のフィールドに定義外の値をセットする。
    Act:
        history.full_clean() でバリデーションを実行する。
    Assert:
        - ValidationErrorが発生すること。
        - エラーメッセージ内に該当フィールド名が含まれていること。
    """
    data: dict[str, Any] = {
        "user": valid_user,
        "opponent_type": GameSession.OpponentType.RANDOM,
        "result": MatchHistory.Result.LOSS,
    }
    data[field] = invalid_value
    history = MatchHistory(**data)

    with pytest.raises(ValidationError) as excinfo:
        history.full_clean()

    assert field in excinfo.value.message_dict


@pytest.mark.django_db
def test_matchhistory_null_constraints() -> None:
    """
    [異常系] MatchHistoryにおいて必須フィールド(user)が欠落している場合、ValidationErrorが発生すること。

    Arrange:
        userフィールドを除いた状態でMatchHistoryを初期化する。
    Act:
        history.full_clean() でバリデーションを実行する。
    Assert:
        - ValidationErrorが発生すること。
        - エラーメッセージ内に 'user' 関連のメッセージが含まれていること。
    """
    history = MatchHistory(
        opponent_type=GameSession.OpponentType.AI, result=MatchHistory.Result.DRAW
    )

    with pytest.raises(ValidationError) as excinfo:
        history.full_clean()

    assert "user" in excinfo.value.message_dict
