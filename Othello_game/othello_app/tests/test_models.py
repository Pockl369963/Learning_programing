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
    1. 正常系: 正しいパラメータでGameSessionが正常に作成・保存されること。
    UUIDの自動生成や、DateTimeFieldの自動設定(auto_now/add)も検証する。
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
    2. 異常系 (Choice制約): 定義外のChoices値が設定された場合、ValidationErrorが発生すること。
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
    2. 異常系 (Null制約): 必須フィールド(user)が欠落している場合、ValidationErrorが発生すること。
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
    3. 境界値・データ型異常: user_color および current_turn に対して、
    許容されない整数値を代入した際にバリデーションエラーになること。
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
    3. 境界値・データ型異常: current_board に対して不正な型
    を代入した場合、適切に弾かれる挙動を確認する。
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
    1. 正常系: 正しいパラメータでMatchHistoryが正常に作成・保存されること。
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
    2. 異常系 (Choice制約): MatchHistoryにおける定義外のChoices値が
    設定された場合、ValidationErrorが発生すること。
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
    2. 異常系 (Null制約): MatchHistoryにおいて必須フィールド(user)が
    欠落している場合、ValidationErrorが発生すること。
    """
    history = MatchHistory(
        opponent_type=GameSession.OpponentType.AI, result=MatchHistory.Result.DRAW
    )

    with pytest.raises(ValidationError) as excinfo:
        history.full_clean()

    assert "user" in excinfo.value.message_dict
