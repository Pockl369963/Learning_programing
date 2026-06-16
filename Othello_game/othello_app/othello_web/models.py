# Create your models here.
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# ====================================================================
# Validators
# ====================================================================


def validate_board_format(value):
    """
    盤面データが8x8の2次元配列（リスト）であることを検証するカスタムバリデータ
    テスト要件: 単なる文字列やシリアライズ不能なオブジェクトを弾く
    """
    if not isinstance(value, list):
        raise ValidationError("盤面は配列(リスト)でなければなりません。")

    if len(value) != 8:
        raise ValidationError("盤面の行数は8である必要があります。")

    for row in value:
        if not isinstance(row, list) or len(row) != 8:
            raise ValidationError("盤面の各行は要素数8のリストである必要があります。")


# ====================================================================
# Models
# ====================================================================


class GameSession(models.Model):
    # Choices定義
    OPPONENT_CHOICES = [
        ("ai", "AI"),
        ("random", "Random"),
    ]

    STATUS_CHOICES = [
        ("playing", "Playing"),
        ("finished", "Finished"),
        ("abandoned", "Abandoned"),
    ]

    COLOR_AND_TURN_CHOICES = [
        (1, "Black"),
        (-1, "White"),
    ]

    # フィールド定義
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opponent_type = models.CharField(max_length=20, choices=OPPONENT_CHOICES)
    user_color = models.IntegerField(choices=COLOR_AND_TURN_CHOICES)

    # 盤面はJSONFieldを使用し、型と構造をカスタムバリデータで担保
    current_board = models.JSONField(validators=[validate_board_format])

    current_turn = models.IntegerField(choices=COLOR_AND_TURN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="playing")

    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} - {self.user.username} ({self.status})"


class MatchHistory(models.Model):
    # Choices定義
    OPPONENT_CHOICES = [
        ("ai", "AI"),
        ("random", "Random"),
    ]

    RESULT_CHOICES = [
        ("win", "Win"),
        ("loss", "Loss"),
        ("draw", "Draw"),
    ]

    # フィールド定義
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opponent_type = models.CharField(max_length=20, choices=OPPONENT_CHOICES)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)

    # タイムスタンプ
    played_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.result} vs {self.opponent_type}"
