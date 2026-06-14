import pytest
import numpy as np
from othello_web.game.engine import OthelloGame

def test_initial_board():
    game = OthelloGame()
    assert game.current_player == 1
    assert game.board[3][3] == -1
    assert game.board[3][4] == 1
    assert game.board[4][3] == 1
    assert game.board[4][4] == -1

def test_invalid_moves():
    game = OthelloGame()
    assert not game.is_valid_move(-1, 0)
    assert not game.is_valid_move(8, 8)
    assert not game.is_valid_move(3, 3)
    assert not game.is_valid_move(0, 0)

def test_valid_move_and_flip():
    """石を置いた時の裏返しテスト"""
    game = OthelloGame()
    
    # 黒の初手の一つ (2, 3) は合法手
    assert game.is_valid_move(2, 3)
    
    # 石を置く
    success = game.step(2, 3)
    assert success == True
    
    # ターンが白(-1)に変わっていること
    assert game.current_player == -1
    
    # 挟んだ石が裏返っていること
    assert game.board[3][3] == 1
    
    # 置いた場所に石があること
    assert game.board[2][3] == 1

def test_all_8_directions_and_multiple_flips():
    """全8方向・複数方向同時の裏返し網羅テスト"""
    game = OthelloGame()
    
    # テスト用のカスタム盤面を作成（全て0で初期化）
    game.board = np.zeros((8, 8), dtype=int)
    game.current_player = 1 # 黒番
    
    # (4, 4)の周囲8マスを白(-1)にし、その外側を黒(1)で囲む「星型」の配置
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (-1, -1), (1, -1)]
    for dr, dc in directions:
        game.board[4 + dr][4 + dc] = -1      # 周囲1マス目は白
        game.board[4 + dr*2][4 + dc*2] = 1   # 周囲2マス目は黒
        
    # (4, 4)に黒を置くと、全8方向の白が同時に裏返るはず
    assert game.is_valid_move(4, 4)
    success = game.step(4, 4)
    
    assert success == True
    
    # 置いた場所に石があること
    assert game.board[4][4] == 1
    
    # 全8方向の白石が黒に裏返っていることを確認
    for dr, dc in directions:
        assert game.board[4 + dr][4 + dc] == 1

    assert game.is_done == True
    assert game.winner == 1  # 黒の勝利