import pytest
import os
import tempfile
from othello_web.game.engine import OthelloGame
from othello_web.game.ai import AIPlayer

def test_ai_returns_valid_move():
    """正常系: AIが必ず合法手を返すかのテスト"""
    game = OthelloGame()
    
    # 重みファイルを指定しない場合はランダムな重みで初期化される想定
    ai = AIPlayer()
    
    # AI(白)のターンにするため、黒の初手を打つ
    game.step(2, 3)
    
    # AIに手を考えさせる
    row, col = ai.get_move(game)
    
    # 返された手が盤面内で、かつ合法手であること
    assert 0 <= row < 8
    assert 0 <= col < 8
    assert game.is_valid_move(row, col, player=-1)

def test_ai_initialization_with_invalid_path():
    """異常系: 存在しないモデルパスを渡してもクラッシュせず、ランダム重みで初期化されるか"""
    invalid_path = "non_existent_model.pth"
    ai = AIPlayer(model_path=invalid_path)
    # インスタンス化できていること（例外が起きないこと）を確認
    assert ai is not None
    assert ai.net is not None

def test_ai_initialization_with_dummy_file():
    """異常系: 壊れたファイルや中身が違うファイルを渡してもクラッシュしないか"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"dummy data")
        tmp_name = tmp.name

    try:
        # Pytorchのファイルではないのでロードに失敗するはずだが、例外で落ちない仕様かテスト
        ai = AIPlayer(model_path=tmp_name)
        assert ai is not None
    finally:
        os.remove(tmp_name)

def test_ai_no_valid_moves():
    """エッジケース: 打てる手がない（パスの）状態での挙動テスト"""
    game = OthelloGame()
    ai = AIPlayer()
    
    # 意図的に誰も打てない盤面（例えば全部白）を作り出す
    for r in range(8):
        for c in range(8):
            game.board[r, c] = 1
            
    # この状態で AI に手を考えさせた場合、例外で落ちずに None を返す
    move = ai.get_move(game)
    
    assert move is None