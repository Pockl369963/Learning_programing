import pytest
import uuid
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from othello_web.models import GameSession, MatchHistory

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def valid_user():
    """テスト用の有効なユーザーオブジェクトを提供するフィクスチャ"""
    return User.objects.create_user(username="testuser", password="testpassword123")


@pytest.fixture
def initial_board():
    """オセロの初期状態（8x8）の盤面データを提供するフィクスチャ"""
    board = [[0] * 8 for _ in range(8)]
    board[3][3], board[4][4] = -1, -1  # 白
    board[3][4], board[4][3] = 1, 1  # 黒
    return board


# ====================================================================
# GameSession Model Tests
# ====================================================================


@pytest.mark.django_db
def test_gamesession_create_success(valid_user, initial_board):
    """
    1. 正常系: 正しいパラメータでGameSessionが正常に作成・保存されること。
    UUIDの自動生成や、DateTimeFieldの自動設定(auto_now/add)も検証する。
    """
    session = GameSession(
        user=valid_user,
        opponent_type="ai",
        user_color=1,
        current_board=initial_board,
        current_turn=1,
        status="playing",
    )
    session.full_clean()  # モデルレベルのバリデーションを実行
    session.save()

    assert isinstance(session.id, uuid.UUID)
    assert session.user == valid_user
    assert session.created_at is not None
    assert session.updated_at is not None
    assert session.status == "playing"


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
def test_gamesession_invalid_choices(valid_user, initial_board, field, invalid_value):
    """
    2. 異常系 (Choice制約): 定義外のChoices値が設定された場合、ValidationErrorが発生すること。
    """
    data = {
        "user": valid_user,
        "opponent_type": "ai",
        "user_color": 1,
        "current_board": initial_board,
        "current_turn": 1,
        "status": "playing",
    }
    data[field] = invalid_value
    session = GameSession(**data)

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert field in excinfo.value.message_dict


@pytest.mark.django_db
def test_gamesession_null_constraints(initial_board):
    """
    2. 異常系 (Null制約): 必須フィールド(user)が欠落している場合、ValidationErrorが発生すること。
    """
    session = GameSession(
        opponent_type="ai",
        user_color=1,
        current_board=initial_board,
        current_turn=1,
        status="playing",
    )

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert "user" in excinfo.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_val", [0, 2, -2, 100])
def test_gamesession_color_and_turn_boundary_validation(
    valid_user, initial_board, invalid_val
):
    """
    3. 境界値・データ型異常: user_color および current_turn に対して、
    1(黒), -1(白) 以外の整数値を代入した際にバリデーションエラーになること。
    ※モデル側で制約（ChoicesやValidators）が強制されているかを検証する。
    """
    session = GameSession(
        user=valid_user,
        opponent_type="ai",
        user_color=invalid_val,  # 許容されない値
        current_board=initial_board,
        current_turn=invalid_val,  # 許容されない値
        status="playing",
    )

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert "user_color" in excinfo.value.message_dict
    assert "current_turn" in excinfo.value.message_dict


@pytest.mark.django_db
def test_gamesession_invalid_current_board_type(valid_user):
    """
    3. 境界値・データ型異常: current_board に対して不正な型(例: 単なる文字列やシリアライズ不能なオブジェクト)
    を代入した場合、適切に弾かれる挙動を確認する。
    ※ここではモデル側で「盤面は配列(リスト)でなければならない」というカスタムバリデーションを
    実装する前提で、ValidationErrorを期待する設計としている。
    """
    session = GameSession(
        user=valid_user,
        opponent_type="ai",
        user_color=1,
        current_board="This is not an 8x8 array",  # 不正なデータ型
        current_turn=1,
        status="playing",
    )

    with pytest.raises(ValidationError) as excinfo:
        session.full_clean()

    assert "current_board" in excinfo.value.message_dict


# ====================================================================
# MatchHistory Model Tests
# ====================================================================


@pytest.mark.django_db
def test_matchhistory_create_success(valid_user):
    """
    1. 正常系: 正しいパラメータでMatchHistoryが正常に作成・保存されること。
    """
    history = MatchHistory(user=valid_user, opponent_type="ai", result="win")
    history.full_clean()
    history.save()

    assert history.id is not None
    assert history.user == valid_user
    assert history.played_at is not None
    assert history.result == "win"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("opponent_type", "human"),  # 'ai', 'random' 以外
        ("result", "surrender"),  # 'win', 'loss', 'draw' 以外
    ],
)
def test_matchhistory_invalid_choices(valid_user, field, invalid_value):
    """
    2. 異常系 (Choice制約): MatchHistoryにおける定義外のChoices値が
    設定された場合、ValidationErrorが発生すること。
    """
    data = {"user": valid_user, "opponent_type": "random", "result": "loss"}
    data[field] = invalid_value
    history = MatchHistory(**data)

    with pytest.raises(ValidationError) as excinfo:
        history.full_clean()

    assert field in excinfo.value.message_dict


@pytest.mark.django_db
def test_matchhistory_null_constraints():
    """
    2. 異常系 (Null制約): MatchHistoryにおいて必須フィールド(user)が
    欠落している場合、ValidationErrorが発生すること。
    """
    history = MatchHistory(opponent_type="ai", result="draw")

    with pytest.raises(ValidationError) as excinfo:
        history.full_clean()

    assert "user" in excinfo.value.message_dict
