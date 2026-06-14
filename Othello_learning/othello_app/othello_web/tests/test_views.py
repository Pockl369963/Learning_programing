import pytest
import json
from django.urls import reverse


@pytest.mark.django_db
def test_api_reset(client):
    """正常系: 初期化APIのテスト"""
    response = client.get(reverse('api_reset'))
    assert response.status_code == 200
    data = response.json()
    assert 'board' in data
    assert data['current_player'] == 1

@pytest.mark.django_db
def test_api_move_valid(client):
    """正常系: 手を進めるAPIのテスト"""
    client.get(reverse('api_reset'))
    response = client.post(
        reverse('api_move'),
        data=json.dumps({'row': 2, 'col': 3}),
        content_type='application/json'
    )
    assert response.status_code == 200
    assert response.json()['valid'] == True

@pytest.mark.django_db
def test_api_move_invalid_method(client):
    """異常系: 不正なHTTPメソッド（GETなど）を弾くテスト"""
    response = client.get(reverse('api_move'))
    assert response.status_code == 405

@pytest.mark.django_db
def test_api_move_invalid_input(client):
    """異常系: 不正なJSONや値がない場合 (400 Bad Request)"""
    client.get(reverse('api_reset'))
    response = client.post(
        reverse('api_move'),
        data=json.dumps({'row': 'abc'}), # 数値以外
        content_type='application/json'
    )
    assert response.status_code == 400

@pytest.mark.django_db
def test_api_move_illegal_move(client):
    """異常系: オセロのルール上置けない場所 (valid=False)"""
    client.get(reverse('api_reset'))
    # (0, 0) は初期状態では置けない
    response = client.post(
        reverse('api_move'),
        data=json.dumps({'row': 0, 'col': 0}),
        content_type='application/json'
    )
    assert response.status_code == 200
    assert response.json()['valid'] == False

@pytest.mark.django_db
def test_api_move_not_your_turn(client):
    """異常系: 相手のターンに人間が打とうとした場合 (400)"""
    client.get(reverse('api_reset'))
    client.post(reverse('api_move'), data=json.dumps({'row': 2, 'col': 3}), content_type='application/json')
    
    # そのまま連続して黒が打とうとする（白のターンなのに）
    response = client.post(
        reverse('api_move'),
        data=json.dumps({'row': 2, 'col': 2}),
        content_type='application/json'
    )
    assert response.status_code == 400

@pytest.mark.django_db
def test_api_ai_move(client, monkeypatch):
    """正常系: AIの手を実行するAPIのテスト"""
    client.get(reverse('api_reset'))
    client.post(reverse('api_move'), data=json.dumps({'row': 2, 'col': 3}), content_type='application/json')
    
    # AI_AGENT の get_move をモック化してテストを安定・高速化させる
    from othello_web.game.ai import AIPlayer
    monkeypatch.setattr(AIPlayer, "get_move", lambda self, game: (2, 2))
    
    response = client.get(reverse('api_ai_move'))
    assert response.status_code == 200
    data = response.json()
    assert 'ai_move' in data
    assert data['current_player'] == 1 # AI(白:-1)が打った後なので黒(1)に戻る