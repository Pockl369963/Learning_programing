import uuid
import random
from datetime import timedelta
from django.utils import timezone
from django.db import transaction, DatabaseError
from django.contrib.auth.models import User
from othello_web.models import GameSession, MatchHistory
from model.othello_env import OthelloEnv


@transaction.atomic
def start_game(user: User, opponent: str) -> GameSession:
    """
    新しいゲームセッションを開始し、ユーザーの先手/後手をランダムに決定します。
    進行中のゲームがある場合は、事前に強制終了（abandoned）させます。
    """
    try:
        # 仕様上1つのゲームしか進行できないとして、進行中のゲームがあれば強制終了する
        handle_abandoned_game(user)

        # 1(黒/先手) または -1(白/後手) をランダムに選択 (マジックナンバーを排除)
        user_color = random.choice([GameSession.Color.BLACK, GameSession.Color.WHITE])  # nosec B311

        session = GameSession.objects.create(
            user=user,
            opponent_type=opponent,
            status=GameSession.Status.PLAYING,
            user_color=user_color,
            current_board=OthelloEnv().get_initial_board(),
            current_turn=GameSession.Color.BLACK,
        )
        return session
    except DatabaseError:
        # DB起因のエラーハンドリング
        raise


@transaction.atomic
def handle_abandoned_game(user: User) -> None:
    """
    進行中(playing)のゲームがあればabandoned状態に変更し、敗北(loss)として履歴に記録します。
    """
    try:
        # 進行中のゲームセッションを取得
        active_sessions = GameSession.objects.filter(
            user=user, status=GameSession.Status.PLAYING
        )

        if not active_sessions.exists():
            return

        # 履歴保存用にリスト化しておく
        sessions_to_abandon = list(active_sessions)

        # ステータスを一括更新（バルクアップデートでN+1回避）
        active_sessions.update(status=GameSession.Status.ABANDONED)

        # 敗北として履歴を保存
        for session in sessions_to_abandon:
            save_match_history(
                user=user, session=session, result=MatchHistory.Result.LOSS
            )
    except DatabaseError:
        raise


@transaction.atomic
def save_match_history(user: User, session: GameSession, result: str) -> None:
    """
    対戦履歴を保存し、ユーザーごとに最新の指定件数のみを保持します。
    上限を超えた場合、最古の履歴をアトミックに削除します。
    """
    try:
        # 新しい履歴を作成
        MatchHistory.objects.create(
            user=user, opponent_type=session.opponent_type, result=result
        )

        # 保持すべき最新件数のIDを取得 (MAX_MATCH_HISTORYはモデル管理へ移行)
        recent_ids = list(
            MatchHistory.objects.filter(user=user)
            .order_by("-pk")[: MatchHistory.MAX_MATCH_HISTORY]
            .values_list("id", flat=True)
        )

        # 最新件数に含まれない古いレコードを物理削除
        MatchHistory.objects.filter(user=user).exclude(id__in=recent_ids).delete()
    except DatabaseError:
        raise


@transaction.atomic
def surrender_game(user: User, session_id: uuid.UUID) -> None:
    """
    自分の進行中のゲームをサレンダー（投了）します。
    ステータスがFINISHEDになり、敗北(LOSS)履歴が保存されます。
    """
    try:
        session = GameSession.objects.get(id=session_id, user=user)

        if session.status != GameSession.Status.PLAYING:
            raise ValueError("サレンダーできるのは進行中のゲームのみです")

        session.status = GameSession.Status.FINISHED
        session.save(update_fields=["status", "updated_at"])

        save_match_history(user=user, session=session, result=MatchHistory.Result.LOSS)
    except DatabaseError:
        raise


@transaction.atomic
def process_timeout_abandoned_games() -> int:
    """
    1時間以上操作がないPLAYING状態のゲームをABANDONEDに変更し、LOSS履歴を作成します。
    """
    try:
        timeout_threshold = timezone.now() - timedelta(hours=1)

        timeout_sessions = GameSession.objects.filter(
            status=GameSession.Status.PLAYING, updated_at__lt=timeout_threshold
        )

        sessions_to_process = list(timeout_sessions)
        processed_count = len(sessions_to_process)

        if processed_count == 0:
            return 0

        timeout_sessions.update(status=GameSession.Status.ABANDONED)

        for session in sessions_to_process:
            save_match_history(
                user=session.user, session=session, result=MatchHistory.Result.LOSS
            )

        return processed_count
    except DatabaseError:
        raise
