# ディレクトリ・ファイル構成

本プロジェクト（オセロAI Webアプリケーション）のディレクトリ構成を詳細に定義します。
フロントエンドのビルド環境（Vite + TailwindCSS）、バックエンド（Django）、AI（PyTorchによるDQN実装）、およびテスト環境を統合した構成です。

```text
Othello_game/
├── docs/                           # ドキュメント群
│   ├── requirements/               # 要件定義関連ファイル
│   └── prompts/                    # プロンプト駆動開発用ファイル群 (機能ごとのテストやロジック生成指示・制約・I/Oを定義したMarkdown)
├── othello_app/                    # Djangoプロジェクトルート
│   ├── config/                     # プロジェクト全体の設定
│   │   ├── settings.py             # 環境変数やアプリ設定
│   │   ├── urls.py                 # 全体ルーティング
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── othello_web/                # Webアプリケーション層 (Django App)
│   │   ├── migrations/             # DBマイグレーションファイル
│   │   ├── models.py               # データアクセス層 (User, MatchHistory, GameSession等)
│   │   ├── views.py                # リクエスト/レスポンスハンドリング (すべてCBVで実装)
│   │   ├── services.py             # ビジネスロジック層 (AI推論呼出, 勝敗判定, トランザクション処理)
│   │   ├── urls.py                 # othello_web固有のルーティング
│   │   └── templates/              # HTMLテンプレート
│   │       ├── base.html           # 全体レイアウト (Tailwindの読み込み)
│   │       ├── auth/               # ログイン・登録画面
│   │       └── game/               # 対戦画面・履歴表示画面
│   ├── model/                      # AIモデル (DQN) 関連コード・重みファイル
│   │   ├── dqn_model.py            # DQNのネットワークアーキテクチャ定義 (PyTorch: nn.Module)
│   │   ├── agent.py                # 推論（次の手を決める）ロジック
│   │   ├── othello_env.py          # オセロの盤面状態管理・合法手判定ロジック
│   │   └── weights/                # 学習済みの重みファイル (例: best_model.pth)
│   ├── frontend/                   # フロントエンドのビルド環境 (Vite + TailwindCSS)
│   │   ├── src/                    # フロントエンドソース
│   │   │   ├── css/                # Tailwindエントリーポイント (input.css)
│   │   │   └── js/                 # API非同期通信(Fetch)、盤面描画、コイントス演出などのJSモジュール
│   │   ├── package.json            # Node.jsパッケージ定義 (E2Eテスト Playwright 等を含む)
│   │   ├── tailwind.config.js      # Tailwindの設定ファイル
│   │   └── vite.config.js          # Viteのビルド設定ファイル (Djangoと連携)
│   ├── tests/                      # バックエンド用テストコード (pytest)
│   │   ├── test_models.py          # DBモデルのテスト
│   │   ├── test_views.py           # CBVのテスト
│   │   ├── test_services.py        # ビジネスロジック・トランザクションのテスト（※AI推論agent.pyは完全にモック化し、固定/ランダムな合法手を返すダミーを利用する）
│   │   └── test_ai.py              # AI推論モジュールの単体テスト
│   ├── manage.py                   # Djangoエントリポイント
│   └── db.sqlite3                  # SQLiteデータベースファイル
├── pyproject.toml                  # バックエンドの依存関係 (uv), Linter/Formatter (Ruff) 設定
└── README.md                       # プロジェクト概要
```

## アーキテクチャ上の責務分割のポイント
* **AIとWebの分離:** DQNのネットワークや推論コードは `model/` に集約し、DjangoのViewから直接呼ばず、必ず `othello_web/services.py` 経由でカプセル化して呼び出します。
* **フロントエンドの分離:** `frontend/` にてViteによるビルドプロセスを実行し、出力されたアセットをDjangoのTemplateから読み込みます。JSロジックやCSS管理はDjangoから切り離しています。
* **CBVとService層:** `views.py` はCBVを採用し、ルーティングとリクエストの受け渡しに専念させます。盤面の検証やDBの保存(トランザクション)等の複雑なロジックはすべて `services.py` に記述し、テストを容易にします。
