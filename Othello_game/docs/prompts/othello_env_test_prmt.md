あなたはシニアのPythonバックエンドエンジニアおよびQAスペシャリストです。
以下の要件に従って、プロダクトレベルのテストコードを実装してください。

# コンテキスト
* オセロの盤面状態管理・合法手判定ロジックをカプセル化した `othello_env.py`（`OthelloEnv` クラス）の単体テストを `pytest` を用いて実装します。
* テストファイル名は `test_othello_env.py` とし、将来的なリファクタリングにも耐えうる、保守性が高く堅牢なテストスイートを構築してください。

# 要件
* 関数名: `test_othello_env.py` 内の各テスト関数（例: `test_get_initial_board`, `test_apply_move_valid`, `test_apply_move_invalid` など）
* 処理内容: `OthelloEnv` クラスのすべてのパブリックメソッド（`get_initial_board`, `is_valid_move`, `apply_move`, `has_valid_moves`, `change_turn`, `calculate_winner`）および、重要なプライベートメソッド（`_validate_board`, `_get_flippable_discs`）の正常系・異常系を完全に網羅して検証する。

# 入力 (Input)
* 盤面状態: `@pytest.fixture` を活用し、以下の状態をセットアップして各テストに提供すること。
  - `initial_board` (初期状態)
  - `mid_game_board` (複数方向が裏返せる複雑な盤面)
  - `pass_board` (一方のプレイヤーに合法手がない状態)
  - `full_board` (石がすべて埋まった決着状態)
* 入力パラメータ: `@pytest.mark.parametrize` を活用し、座標 (row, col) やプレイヤー情報 (1, -1, 不正な値) の様々な組み合わせ（境界値、盤面外、既存の石の上など）を注入すること。

# 出力 (Output)
* すべてのテストが独立して実行可能であり、状態の汚染（副作用）がない `pytest` テストコード。
* アサーションは `assert` 文を用いて、盤面の配列状態、期待される真偽値、または辞書の値（勝敗判定など）を厳密に評価すること。

# 制約事項・エッジケース (Constraints)
1. 【型定義】: テストコード内でも、可能な限りPython 3.12+ の最新の型ヒント（`typing` モジュール等）を使用すること。
2.  盤面データの比較や更新テストの際は、参照渡しによるミューテーションを防ぐため、必要に応じて `copy.deepcopy` を考慮すること。
3. 【例外処理の検証】: 異常系（リストでない盤面、サイズが8x8以外の盤面、0/1/-1以外の不正な値、盤面外アクセス、置けない場所への手）に対しては、必ず `pytest.raises(ValueError, match="期待されるエラーメッセージの一部")` を用いて、例外の型だけでなくメッセージ内容まで厳密に検証すること。
4. 【ドキュメンテーション】: 各テスト関数にはGoogleスタイルのDocstringを記述し、「Arrange (準備) / Act (実行) / Assert (検証)」の3フェーズが明確にわかるようにインラインコメントを記述すること。
5. 【DRY原則】: 重複するセットアップコードは書かず、クラスベースのテストグループ化（`class TestApplyMove:` など）やフィクスチャを駆使して可読性を高めること。