あなたはシニアのPythonバックエンドエンジニア、兼QAエンジニアです。
以下の要件に従って、Djangoアプリケーションのビジネスロジック層に対するプロダクトレベルのテストコード（`test_services.py`）をゼロから実装してください。

# コンテキスト
* オセロWebアプリケーションの Service層 (`services.py`) のテストコードを作成します。
* 盤面の初期化や合法手判定などの純粋なドメインロジックは `othello_env.py` に分離されています。Service層は「ゲームセッションの管理（DB保存）」「トランザクション制御」「勝敗履歴の保存ルール」などのビジネスロジックに専念しています。
* テストには `pytest`、`pytest-django`、`pytest-mock` を使用します。

# 要件
以下の3つのService関数の振る舞いを検証するテストクラス `TestOthelloServices` を実装してください。

1. `start_game(user, opponent: str) -> GameSession`
2. `handle_abandoned_game(user) -> None`
3. `save_match_history(user, session, result: str) -> None`

# テスト対象の入力とアサーションの期待値 (Inputs & Expected Assertions)

## 1. `test_start_game` (正常系)
* **入力:** テスト用ユーザー(`User`インスタンス)、対戦相手の種別(`"ai"` または `"random"`)
* **モック:** `random.choice` をモック化し、ユーザーの先手(1)・後手(-1)を固定する。盤面の初期化ロジック(`othello_env.get_initial_board`等)がService内で呼ばれている場合は、それも適宜モック化または利用する。
* **期待値:**
  * 返り値の `GameSession` インスタンスが正しく作成されていること。
  * `status == "playing"` であること。
  * `user_color` がモックで指定した値(1 または -1)と一致すること。

## 2. `test_handle_abandoned_game` (正常系・異常系)
* **入力:** `status="playing"` のセッションを持つユーザー、および持たないユーザー。
* **期待値:**
  * (正常系) `playing` のセッションの `status` が `abandoned` に更新されること。
  * (正常系) 連動して `MatchHistory` に `result="loss"` として敗北履歴が保存されること。
  * (異常系) 進行中のゲームがない場合は、何も変更されずエラーも起きないこと。

## 3. `test_save_match_history` (正常系・境界値)
* **入力:** 既に9件の履歴を持つユーザー、既に10件の履歴を持つユーザー。
* **期待値:**
  * 新しい履歴を追加した際、全体の件数が最大10件に保たれていること。
  * 11件目となる履歴が追加された場合、アトミックに「最古のレコード」が削除され、最新の履歴が正しく追加されていること。

# 制約事項・エッジケース (Constraints)
1. **型定義の厳密化 (`mypy --strict` 準拠):**
   * すべての関数・テストメソッドの引数と戻り値に型ヒントを付与してください（テストメソッドの戻り値は `-> None`）。
   * `pytest-mock` を使用する際、モック引数の型は `mocker: MockerFixture` としてください（`from pytest_mock import MockerFixture` をインポート）。
   * フィクスチャの戻り値にも適切な型ヒントを記述してください。
2. **データベースへのアクセス:**
   * テストクラスには `@pytest.mark.django_db` デコレータを付与してください。
3. **品質と可読性:**
   * Arrange-Act-Assert (準備-実行-検証) のパターンに従ってコメントで区切り、可読性を高めてください。
   * クラスや各テストメソッドには、テストの意図を明確にするDocstring（Googleスタイル等）を記述してください。
4. **マジックナンバーの排除:**
   * マジックナンバーは避け、定数やEnumに近い形で表現、または意図をコメントで補足してください。