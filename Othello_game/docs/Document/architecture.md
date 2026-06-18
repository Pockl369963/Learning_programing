# Othello Application Architecture & Logic Reference

このドキュメントは、Othelloアプリケーションのデータベーススキーマ、サービス層（`services.py`）、およびAI/DQNロジックの依存関係と全体像をまとめたものです。
リファクタリング、デバッグ、アップデート、およびAIによるコード生成のコンテキストとして活用してください。

---

## 1. データベース・モデル層 (`models.py`)

Django ORMを使用して定義されています。

### 1.1 `GameSession` モデル
進行中・完了済みのオセロのゲーム状態を管理します。

* **`id`**: UUID (Primary Key)
* **`user`**: `User` モデルへの外部キー。
* **`opponent_type`**: 対戦相手の種類 (`"ai"` または `"random"`)。
* **`user_color`**: ユーザーの石の色 (`1`: Black/先手, `-1`: White/後手)。
* **`current_board`**: 8x8の2次元配列を格納する `JSONField`。カスタムバリデータ (`validate_board_format`) で厳密に型と構造が検証されます。
* **`current_turn`**: 現在の手番 (`1` または `-1`)。
* **`status`**: ゲームの進行状況 (`"playing"`, `"finished"`, `"abandoned"`)。
* **タイムスタンプ**: `created_at`, `updated_at` (自動更新)。

### 1.2 `MatchHistory` モデル
対戦結果の履歴を管理します。ユーザーごとに最大10件（`MAX_MATCH_HISTORY`）のみ保持されます。

* **`user`**: `User` モデルへの外部キー。
* **`opponent_type`**: `GameSession` と同様。
* **`result`**: 勝敗 (`"win"`, `"loss"`, `"draw"`)。
* **タイムスタンプ**: `played_at`

---

## 2. サービス層 (`services.py`)

Webリクエスト（View層）とデータ・環境操作（Model/Env層）を繋ぐビジネスロジックの中核です。全関数に `@transaction.atomic` が付与され、整合性を担保しています。

### 2.1 排他制御とバリデーション (Optimistic Locking)
* **`process_move`**: ユーザーが石を置く際の最重要処理。
  1. **状態確認**: セッションが `PLAYING` であるかをチェック。
  2. **排他制御 (TurnConflictError)**: リクエストの `expected_turn` とDBの `current_turn` が一致するか確認（連打や複数ウィンドウによる状態不整合を防ぐため、不一致なら HTTP 409 相当のエラーを発生）。
  3. **合法手チェック (InvalidMoveError)**: `OthelloEnv.is_valid_move` でルール違反がないか確認（違反なら HTTP 400 相当のエラー）。
  4. **盤面更新**: `OthelloEnv.apply_move` と `change_turn` を呼び出し、DBへ保存。

### 2.2 セッションと履歴のライフサイクル管理
* **`start_game`**: 進行中のゲーム（`PLAYING`）を検知した場合、自動的に `ABANDONED`（放棄・敗北扱い）にしてから新ゲームを作成します。ユーザーの色はランダムに決定されます。
* **`surrender_game` / `process_timeout_abandoned_games`**: ユーザーの明示的な降伏、または1時間以上の放置（タイムアウト）時にセッションを終了し、敗北履歴を記録します。
* **`save_match_history`**: 履歴追加時に、最新10件をクエリで特定し、それより古いレコードを一括削除（クリーンアップ）します。

---

## 3. AI / DQNロジック (`Agent.py`, `dqn_model.py`)

PyTorchで実装された深層強化学習（Distributional DQN）ベースのAIモデルです。

### 3.1 ネットワークアーキテクチャ (`dqn_model.py`)
* **SEResNetBlock (Squeeze-and-Excitation)**: 特徴量のチャネル間の依存関係を学習できるSEアテンション機構を取り入れたResNetブロックを採用しています。
* **Dueling Network + C51**: 
  * 状態価値（Value）と行動利得（Advantage）を別々に計算して合成します。
  * 出力は単一のQ値ではなく、**C51（カテゴリカルDQN）**に基づく51個のAtom（確率分布）です。出力Shapeは `(Batch, 64, 51)` となります。

### 3.2 AIエージェントロジック (`Agent.py`)
AIの推論を安全かつルールに沿って実行するためのラッパーです。

* **Observation生成 (`_get_observation`)**:
  8x8の盤面を、DQNが理解しやすい `(3, 8, 8)` のテンソル（特徴量マップ）に変換します。
  * **チャンネル0**: 自分の石 (1.0 or 0.0)
  * **チャンネル1**: 相手の石 (1.0 or 0.0)
  * **チャンネル2**: 合法手の位置フラグ (1.0 or 0.0)
* **推論とAction Masking (`get_move`)**:
  1. Observationをネットワークに入力し、確率分布（`q_log_probs`）を取得。
  2. `V_MIN` から `V_MAX` の範囲（51等分）のサポート値と確率を内積し、各マスの期待値（Q値）を算出。
  3. **合法手マスキング**: ルール違反を防ぐため、**合法手でないマスのQ値を強制的に `-1e10` に設定**します。ネットワークが未熟でも非合法手を選ぶことはありません。
  4. 最大Q値のインデックスから、行（Row）と列（Col）を算出。
* **耐障害性**: `__init__` での重みロード時に例外をキャッチする構造を持ち、ファイル破損等でロードに失敗してもクラッシュせず、初期化された重みで安全に起動を継続します。
