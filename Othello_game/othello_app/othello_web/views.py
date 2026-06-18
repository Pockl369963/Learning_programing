import json
import logging
import random
import uuid
from typing import Any, Dict, List, Optional, cast

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin

from othello_web.models import GameSession, MatchHistory
from othello_web.services import (
    start_game,
    process_move,
    TurnConflictError,
    InvalidMoveError,
)
from model.othello_env import OthelloEnv
from model.Agent import AIPlayer

logger = logging.getLogger(__name__)


def _finish_game(session: GameSession, env: OthelloEnv) -> None:
    """ゲーム終了時の処理を行い、勝敗履歴を保存する。"""
    session.status = GameSession.Status.FINISHED
    session.save(update_fields=["status", "updated_at"])

    winner_info = env.calculate_winner(session.current_board)
    winner = winner_info["winner"]

    if winner == session.user_color:
        result = MatchHistory.Result.WIN
    elif winner == OthelloEnv.EMPTY:
        result = MatchHistory.Result.DRAW
    else:
        result = MatchHistory.Result.LOSS

    from othello_web.services import save_match_history

    save_match_history(user=session.user, session=session, result=result)


def _check_and_run_ai_turns(session: GameSession) -> None:
    """
    セッションの状態を確認し、AIのターンであれば自動的に手を打つループ。
    また、パスやゲーム終了判定もここで行う。
    """
    env = OthelloEnv()

    # 相手がAIの場合にのみAIPlayerを初期化
    agent: Optional[AIPlayer] = None
    if session.opponent_type == GameSession.OpponentType.AI:
        agent = AIPlayer()

    while session.status == GameSession.Status.PLAYING:
        has_moves_black = env.has_valid_moves(
            session.current_board, OthelloEnv.PLAYER_BLACK
        )
        has_moves_white = env.has_valid_moves(
            session.current_board, OthelloEnv.PLAYER_WHITE
        )

        # 1. 終了判定: 両者とも合法手がない場合はゲーム終了
        if not has_moves_black and not has_moves_white:
            _finish_game(session, env)
            break

        # 2. ターンの進行
        if session.current_turn == session.user_color:
            # ユーザーの手番
            if not env.has_valid_moves(session.current_board, session.user_color):
                # ユーザーが合法手を持たない場合、強制パスしてターンを相手に渡す
                session.current_turn = env.change_turn(session.user_color)
                session.save(update_fields=["current_turn", "updated_at"])
                continue
            else:
                # ユーザーに合法手がある場合は、ユーザーの入力を待つためループを抜ける
                break
        else:
            # AI(相手)の手番
            if not env.has_valid_moves(session.current_board, session.current_turn):
                # AIが合法手を持たない場合、強制パスしてターンをユーザーに渡す
                session.current_turn = session.user_color
                session.save(update_fields=["current_turn", "updated_at"])
                continue

            # AIが手を打つ
            move = None
            if session.opponent_type == GameSession.OpponentType.RANDOM:
                # ランダムAIの場合
                valid_moves = []
                for r in range(8):
                    for c in range(8):
                        if env.is_valid_move(
                            session.current_board, session.current_turn, r, c
                        ):
                            valid_moves.append((r, c))
                if valid_moves:
                    move = random.choice(valid_moves)  # nosec B311
            else:
                # 通常のAIPlayerの場合
                if agent is not None:
                    move = agent.get_move(
                        session.current_board, current_player=session.current_turn
                    )

            if move is None:
                # 手がない場合はパス (本来は到達しないはずだが念のため)
                session.current_turn = session.user_color
                session.save(update_fields=["current_turn", "updated_at"])
                continue

            row, col = move
            # AIの手を適用
            process_move(
                user=session.user,
                session_id=session.id,
                row=row,
                col=col,
                expected_turn=session.current_turn,
            )
            # process_moveでDBが更新されたため、最新状態を反映
            session.refresh_from_db()


class GameStartView(LoginRequiredMixin, View):
    """
    ゲーム開始API
    POST /api/game/start/
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            data: Dict[str, Any] = json.loads(request.body)
            opponent_str: str = data.get("opponent", "")

            # opponentの妥当性チェック
            valid_opponents = [
                GameSession.OpponentType.AI,
                GameSession.OpponentType.RANDOM,
            ]
            if not opponent_str or opponent_str not in valid_opponents:
                return JsonResponse({"error": "無効な対戦相手タイプです"}, status=400)

            user = cast(User, request.user)
            session: GameSession = start_game(
                user=user,
                opponent=opponent_str,
            )

            # AIが先手の場合のループ処理などを実行
            _check_and_run_ai_turns(session)
            session.refresh_from_db()

            response_data = {
                "session_id": str(session.id),
                "status": session.status,
                "user_color": session.user_color,
                "current_board": session.current_board,
                "current_turn": session.current_turn,
            }
            return JsonResponse(response_data, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "無効なJSON形式です"}, status=400)
        except Exception:
            logger.exception("ゲーム開始処理中にエラーが発生しました")
            return JsonResponse({"error": "内部サーバーエラー"}, status=500)


class GameMoveView(LoginRequiredMixin, View):
    """
    ゲーム進行API
    POST /api/game/move/
    """

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            data: Dict[str, Any] = json.loads(request.body)

            # 必須パラメータのチェック
            required_keys = ["session_id", "row", "col", "expected_turn"]
            if not all(key in data for key in required_keys):
                return JsonResponse(
                    {"error": "必要なパラメータが不足しています"}, status=400
                )

            # UUID形式の簡易チェック
            try:
                session_id: uuid.UUID = uuid.UUID(str(data["session_id"]))
            except ValueError:
                return JsonResponse({"error": "無効なセッションID形式です"}, status=400)

            row: int = int(data["row"])
            col: int = int(data["col"])
            expected_turn: int = int(data["expected_turn"])

            # process_move を呼び出し (内部でGameSessionの取得・バリデーション・状態更新を行う)
            try:
                user = cast(User, request.user)
                session: GameSession = process_move(
                    user=user,
                    session_id=session_id,
                    row=row,
                    col=col,
                    expected_turn=expected_turn,
                )
            except GameSession.DoesNotExist:
                return JsonResponse({"error": "セッションが見つかりません"}, status=404)

            # AIターンの進行と終了判定
            _check_and_run_ai_turns(session)
            session.refresh_from_db()

            response_data = {
                "status": session.status,
                "current_board": session.current_board,
                "current_turn": session.current_turn,
            }
            return JsonResponse(response_data, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "無効なJSON形式です"}, status=400)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except TurnConflictError as e:
            return JsonResponse({"error": str(e)}, status=409)
        except InvalidMoveError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception:
            logger.exception("ゲーム進行処理中にエラーが発生しました")
            return JsonResponse({"error": "内部サーバーエラー"}, status=500)


class UserHistoryView(LoginRequiredMixin, View):
    """
    ユーザー対戦履歴取得API
    GET /api/user/history/
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            # 最新の履歴を上限件数だけ取得
            user = cast(User, request.user)
            histories = MatchHistory.objects.filter(user=user).order_by("-played_at")[
                : MatchHistory.MAX_MATCH_HISTORY
            ]

            history_list: List[Dict[str, Any]] = []
            for h in histories:
                history_list.append(
                    {
                        "opponent_type": h.opponent_type,
                        "result": h.result,
                        "played_at": h.played_at.isoformat() if h.played_at else None,
                    }
                )

            return JsonResponse({"history": history_list}, status=200)

        except Exception:
            logger.exception("ユーザー履歴取得処理中にエラーが発生しました")
            return JsonResponse({"error": "内部サーバーエラー"}, status=500)
