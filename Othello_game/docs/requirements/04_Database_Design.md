# データベース・データモデル設計

本プロジェクトにおけるデータベース設計と、関連するビジネスルール（制約）を定義します。
アーキテクチャとして「サーバー側検証型 (Stateful)」を採用するため、途中離脱や盤面の状態管理を行うためのテーブル（`GameSession`）も定義しています。

## 主要エンティティ (Django Models)

### 1. `User` モデル
Djangoの標準認証モデル (`django.contrib.auth.models.User`) を利用します。
- 今回の要件に基づき、複雑なプロフィールは持たず、「ユーザー名」と「パスワード」のみでの登録・認証を基本とします。

### 2. `GameSession` モデル (対戦セッション管理)
対戦中の盤面状態をサーバー側で保持し、クライアントからの不正なAPIリクエスト（チート）を防ぎつつ、ブラウザ離脱（途中離脱）を検知するためのモデルです。

- **フィールド構成:**
  - `id`: Primary Key (UUIDを推奨)
  - `user`: ForeignKey (`User` に紐付け, CASCADE)
  - `opponent_type`: CharField (Choices: 'ai', 'random')
  - `user_color`: IntegerField (1: 黒/先手, -1: 白/後手) ※コイントス結果
  - `current_board`: JSONField または TextField (現在の8x8盤面配列の状態)
  - `current_turn`: IntegerField (1 または -1、現在のターン)
  - `status`: CharField (Choices: 'playing', 'finished', 'abandoned') // 離脱検知用
  - `created_at`: DateTimeField (auto_now_add=True)
  - `updated_at`: DateTimeField (auto_now=True)

- **ビジネスルール:**
  - ゲーム開始時 (`/api/game/start/`) に `playing` ステータスでレコードを作成。
  - **排他制御（楽観的ロック）:** `/api/game/move/` の処理時、Service層でDBの `current_turn` とユーザーの手番（白か黒か）を比較し、一致しない場合は処理を中断して `409 Conflict` (または `400 Bad Request`) を返します。これにより連打（ダブルクリック）による不正な複数回ターン実行を防止します。さらに厳密性を担保するため、トランザクション内で `select_for_update()` を用いて行ロックを取得することを推奨します。
  - ユーザーが新しいゲームを開始しようとした際、過去に `playing` ステータスの `GameSession` が残っていれば、それを `abandoned`（途中離脱）に更新すると同時に、後述の `MatchHistory` に `loss` として履歴を記録します。

### 3. `MatchHistory` モデル (対戦履歴)
ユーザーごとに最新10件の勝敗履歴を保存するモデルです。

- **フィールド構成:**
  - `id`: Primary Key
  - `user`: ForeignKey (`User` に紐付け, CASCADE)
  - `opponent_type`: CharField (Choices: 'ai', 'random')
  - `result`: CharField (Choices: 'win', 'loss', 'draw')
  - `played_at`: DateTimeField (auto_now_add=True)

- **ビジネスルール/制約:**
  - **明示的なトランザクションによる最新10件の保持:**
    Service層 (`othello_web/services.py`) で明示的なメソッド内にトランザクション（`transaction.atomic`）を張ります。
    ゲーム終了時（または途中離脱検知時）に「新しい `MatchHistory` レコードを保存」すると同時に、「該当ユーザーの履歴レコード数が10件を超えている場合は、最も古いレコードを物理削除（DELETE）する」という処理を一貫して行います。
  - **途中離脱対応:**
    `GameSession` が `abandoned` になった際、このモデルに `result='loss'` として強制的に敗北の履歴が記録されます。
