# 指示
あなたはDjangoのスペシャリストであり、TDD（テスト駆動開発）を実践するシニアエンジニアです。
現在、オセロWebアプリケーションの開発を行っています。
以下の【前提条件】と【データモデル定義】に基づき、データベースモデルの単体テストコード（`tests/test_models.py`）のみを生成してください。
※実装コード（`models.py`）はまだ出力しないでください。まずはテストが失敗する状態（Red）を作ります。

# 前提条件
* 言語/フレームワーク: Python 3.12, Django 5.2
* テストツール: pytest, pytest-django
* 対象アプリ名: `othello_web`
* テスト対象ファイル: `tests/test_models.py`
* ユーザー認証基盤: Django標準の `django.contrib.auth.models.User` を利用
* トランザクションやビジネスロジック（例：履歴の10件保持制限、楽観的ロック）は `services.py` で実装するため、今回のモデルテストでは純粋なデータモデルの制約検証に集中してください。

# データモデル定義 (契約)
以下の2つのモデルを `othello_web/models.py` に定義する前提でテストを書いてください。

## 1. GameSession (対戦セッション管理)
* `id`: Primary Key (UUID)
* `user`: ForeignKey (`User` に紐付け, CASCADE)
* `opponent_type`: CharField (Choices: 'ai', 'random')
* `user_color`: IntegerField (1: 黒/先手, -1: 白/後手)
* `current_board`: JSONField (現在の8x8盤面配列)
* `current_turn`: IntegerField (1 または -1)
* `status`: CharField (Choices: 'playing', 'finished', 'abandoned')
* `created_at`: DateTimeField (auto_now_add=True)
* `updated_at`: DateTimeField (auto_now=True)

## 2. MatchHistory (対戦履歴)
* `id`: Primary Key
* `user`: ForeignKey (`User` に紐付け, CASCADE)
* `opponent_type`: CharField (Choices: 'ai', 'random')
* `result`: CharField (Choices: 'win', 'loss', 'draw')
* `played_at`: DateTimeField (auto_now_add=True)

# 出力要件
* `pytest-django` の `@pytest.mark.django_db` デコレータを適切に使用すること。
以下の3パターンのテストを網羅すること：
1. **正常系:** 各モデルが正しいパラメータで正常に作成・保存されること。
2. **異常系 (Choice/Null制約):** `.full_clean()` を実行し、定義外のChoices値（例: `status='invalid'`）や、必須フィールドの欠落時に `ValidationError` が発生すること。
3. **境界値・データ型異常:**
   * `user_color` および `current_turn` に対して、`1`, `-1` 以外の整数（例: `0`, `2`）を代入した際にバリデーションエラーになること（モデル側での制約を強制するため）。
   * `current_board` に対して不正な型を代入した場合の挙動。
* テストコードは可読性を高く保ち、Docstringでテストの意図を簡潔に記載すること。
* MarkdownのPythonコードブロック形式で出力すること。