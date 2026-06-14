import json
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from .game.engine import OthelloGame
from .game.ai import AIPlayer

MODEL_PATH = settings.BASE_DIR / 'model' / 'checkpoint_20260131_1627_ep93500.pth'
AI_AGENT = AIPlayer(str(MODEL_PATH))

def index(request):
    """メイン画面の描画"""
    return render(request, 'othello_web/index.html')

def api_reset(request):
    game = OthelloGame()
    _save_game_state(request, game)
    return JsonResponse(_serialize_game_state(game)) 

def api_move(request):
    """人間の手を受け付ける"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        row = int(data.get('row'))
        col = int(data.get('col'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid input'}, status=400)

    game = _load_game_state(request)
    
    if not game.is_done and game.current_player == 1:
        if game.step(row, col):
            _save_game_state(request, game)
            return JsonResponse(_serialize_game_state(game, valid=True))
        else:
            return JsonResponse({'valid': False})
    
    return JsonResponse({'error': 'Not your turn'}, status=400)

def api_ai_move(request):
    game = _load_game_state(request)
    
    if game.is_done or game.current_player != -1:
        return JsonResponse({'error': 'Not AI turn'}, status=400)

    move = AI_AGENT.get_move(game)
    ai_move_coords = None
    if move:
        ai_row, ai_col = move
        game.step(ai_row, ai_col)
        ai_move_coords = [int(ai_row), int(ai_col)]
    else:
        game.change_turn() # パス
        
    _save_game_state(request, game)
    
    data = _serialize_game_state(game)
    data['ai_move'] = ai_move_coords
    return JsonResponse(data)

## ユーティリティ関数

def _serialize_game_state(game, valid=True):
    """ゲーム状態をJSONシリアライズ可能な形式に変換する関数"""
    return {
        'board': game.board.tolist(),
        'current_player': game.current_player,
        'is_done': game.is_done,
        'winner': game.winner,
        'valid': valid,
        'black_count': int(np.sum(game.board == 1)),
        'white_count': int(np.sum(game.board == -1)),
    }

def _save_game_state(request, game):
    """ゲーム状態をセッションに保存するユーティリティ関数"""
    request.session['board'] = game.board.tolist()
    request.session['current_player'] = game.current_player
    request.session['is_done'] = game.is_done
    request.session['winner'] = game.winner

def _load_game_state(request):
    game = OthelloGame()
    board_list = request.session.get('board')
    if board_list:
        game.board = np.array(board_list, dtype=int)
        game.current_player = request.session.get('current_player', 1)
        game.is_done = request.session.get('is_done', False)
        game.winner = request.session.get('winner', None)
    return game


