## Issue 1: DBモデルと基本制約の構築 (Data Access Layer)
* `django.contrib.auth.models.User` を利用したユーザー認証基盤の準備。
* 対戦状態を管理する `GameSession` モデル（`current_board`, `current_turn`, `status` 等）の実装。
* ユーザーごとの対戦履歴を保存する `MatchHistory` モデルの実装。
* `tests/test_models.py` にて、DBスキーマの単体テスト（Red → Green）を実施する。

## Issue 2: ゲーム進行のビジネスロジック実装 (Service Layer)
* `othello_web/services.py` に、ゲーム開始（コイントスによる先手・後手決定）のロジックを実装する。
* トランザクション（`transaction.atomic`）を利用し、`MatchHistory` に履歴を保存する際、最新10件のみを保持して古いレコードを物理削除する処理を実装する。
* `GameSession` が `abandoned`（途中離脱）になった際に、自動的に `loss` の履歴を記録する機能を実装する。
* `tests/test_services.py` にて、AI推論モジュールをモック化した状態でロジックの単体テストを実施する。

## Issue 3: 排他制御とバリデーションの実装 (Service Layer)
* `GameSession` の `current_turn` とユーザーリクエストを比較し、連打（ダブルクリック）を防ぐ楽観的ロック機能（不一致時は409 Conflictエラー）を実装する。
* 盤面の合法手判定ロジック（不正な手の場合は400 Bad Requestエラー）を組み込む。
* これら異常系のテストケースを `tests/test_services.py` に追加・パスさせる。

## Issue 4: APIエンドポイントの実装 (Presentation Layer)
* クラスベースビュー（CBV）を用いて、`POST /api/game/start/`（初期盤面生成・ゲーム開始）を実装する。
* `POST /api/game/move/`（ユーザーの手番と相手の手番の処理、終了判定）を実装する。
* `GET /api/user/history/`（直近10件の履歴取得）を実装する。
* ログインユーザーのみがアクセスできるよう `@login_required` 等のアクセス制御を実装し、`tests/test_views.py` にて各種APIのE2Eライクなテストを実施する。

## Issue 5: オセロAI（DQN）環境の構築と結合
* `model/othello_env.py` にオセロの盤面状態管理と合法手判定の環境ロジックを実装する。
* `model/dqn_model.py` にPyTorchを用いたネットワークアーキテクチャを定義し、`model/agent.py` に推論ロジックを実装する。
* `othello_web/services.py` から `agent.py` を呼び出す連携処理を実装し、`tests/test_ai.py` で単体テストを実施する。

## Issue 6: フロントエンドのビルド環境構築
* `frontend/` ディレクトリ内にViteとTailwindCSSの開発環境をセットアップする。
* DjangoのTemplate（`base.html` など）から、Viteでビルドされたアセット（JS/CSS）を読み込む連携設定を行う。
* `<meta name="csrf-token" content="{{ csrf_token }}">` を利用した、CSRFトークンの受け渡し基盤を構築する。

## Issue 7: 対戦画面と非同期通信 (Vanilla JS) の実装
* 画面遷移を伴わない非同期通信（Fetch API）を用いて、`/api/game/start/` および `/api/game/move/` と通信するJSモジュールを実装する。
* 受け取ったJSONデータ（8x8の二次元配列）を元に、Vanilla JSでオセロ盤面をDOM上に描画・更新する処理を実装する。
* APIリクエストのヘッダーに `X-CSRFToken` を付与する処理を徹底する。

## Issue 8: 履歴・マイページ機能とUI演出の実装
* `/api/user/history/` をFetch APIで取得し、ページ遷移なしでマイページに勝敗履歴をシームレスに表示する処理を実装する。
* ゲーム開始時にコイントスで先手・後手を決定する際の、オセロの駒を投げるアニメーション演出（UX）を実装する。


## Issue 9: E2Eテストの自動化 (Playwright)
* `package.json` にPlaywrightを導入し、ユーザーの一連の操作（ログイン → 対戦開始 → 駒を置く → 勝敗確認）のE2Eテストを作成・実行する。
* 盤面描画やコイントスのアニメーション、API通信の総合的な連携が正しく行われているかを担保する。

## Issue 10: コンテナ環境での動作検証
* ローカル環境（Docker等）でバックエンド・フロントエンド・DBを含むシステム全体を立ち上げる。
* 環境変数やパス設定に問題がないかを検証し、結合テスト環境でのエラーログ確認・修正を行う。
