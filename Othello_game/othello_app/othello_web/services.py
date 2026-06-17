import random
from django.db import transaction
from othello_web.models import GameSession, MatchHistory
from model.othello_env import OthelloEnv

MAX_MATCH_HISTORY = 10


def start_game(user, opponent: str) -> GameSession:
    """
    新しいゲームセッションを開始し、ユーザーの先手/後手をランダムに決定します。
    """
    # 1(黒/先手) または -1(白/後手) をランダムに選択
    user_color = random.choice([1, -1])  # nosec B311

    session = GameSession.objects.create(
        user=user,
        opponent_type=opponent,
        status=GameSession.Status.PLAYING,
        user_color=user_color,
        current_board=OthelloEnv().get_initial_board(),
        current_turn=GameSession.Color.BLACK,
    )
    return session


@transaction.atomic
def handle_abandoned_game(user) -> None:
    """
    進行中(playing)のゲームがあればabandoned状態に変更し、敗北(loss)として履歴に記録します。
    """
    # 進行中のゲームセッションを取得（複数ある場合も考慮）
    active_sessions = GameSession.objects.filter(
        user=user, status=GameSession.Status.PLAYING
    )

    if not active_sessions.exists():
        return

    for session in active_sessions:
        # ステータスを更新
        session.status = GameSession.Status.ABANDONED
        session.save(update_fields=["status"])

        # 敗北として履歴を保存 (内部で最新10件の制約も適用される)
        save_match_history(user=user, session=session, result=MatchHistory.Result.LOSS)


@transaction.atomic
def save_match_history(user, session, result: str) -> None:
    """
    対戦履歴を保存し、ユーザーごとに最新の10件のみを保持します。
    上限を超えた場合、最古の履歴をアトミックに削除します。
    """
    # 新しい履歴を作成
    MatchHistory.objects.create(
        user=user, opponent_type=session.opponent_type, result=result
    )

    # 保持すべき最新10件のIDを取得
    # order_by('-pk') で作成順（降順）に並び替える
    recent_ids = list(
        MatchHistory.objects.filter(user=user)
        .order_by("-pk")[:MAX_MATCH_HISTORY]
        .values_list("id", flat=True)
    )

    # 最新10件に含まれない古いレコードを物理削除
    MatchHistory.objects.filter(user=user).exclude(id__in=recent_ids).delete()
