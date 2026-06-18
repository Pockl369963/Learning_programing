from django.urls import path
from othello_web.views import GameStartView, GameMoveView, UserHistoryView

app_name = "othello_web"

urlpatterns = [
    path("game/start/", GameStartView.as_view(), name="game_start"),
    path("game/move/", GameMoveView.as_view(), name="game_move"),
    path("user/history/", UserHistoryView.as_view(), name="user_history"),
]
