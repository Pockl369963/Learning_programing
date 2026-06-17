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
    class OpponentType(models.TextChoices):
        AI = "ai", "AI"
        RANDOM = "random", "Random"

    class Status(models.TextChoices):
        PLAYING = "playing", "Playing"
        FINISHED = "finished", "Finished"
        ABANDONED = "abandoned", "Abandoned"

    class Color(models.IntegerChoices):
        BLACK = 1, "Black"
        WHITE = -1, "White"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opponent_type = models.CharField(max_length=20, choices=OpponentType.choices)
    user_color = models.IntegerField(choices=Color.choices)

    # 盤面はJSONFieldを使用し、型と構造をカスタムバリデータで担保
    current_board = models.JSONField(validators=[validate_board_format])

    current_turn = models.IntegerField(choices=Color.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLAYING
    )

    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} - {self.user.username} ({self.status})"


class MatchHistory(models.Model):
    class Result(models.TextChoices):
        WIN = "win", "Win"
        LOSS = "loss", "Loss"
        DRAW = "draw", "Draw"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    opponent_type = models.CharField(
        max_length=20, choices=GameSession.OpponentType.choices
    )
    result = models.CharField(max_length=20, choices=Result.choices)

    # タイムスタンプ
    played_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.result} vs {self.opponent_type}"
