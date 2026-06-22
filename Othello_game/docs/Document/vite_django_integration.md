# Django と Vite の連携方法についての解説

現在のプロジェクトでは、`django-vite` というサードパーティライブラリを使用して、DjangoのテンプレートエンジンとViteの強力なフロントエンド開発環境（HMRやビルド機能）を統合しています。

## 1. 現在の連携の仕組み（全体像）

開発環境では、Djangoサーバー（`runserver`）とVite開発サーバー（`vite`）の2つを起動します。
ブラウザからDjangoのページ（例：`http://localhost:8000`）にアクセスすると、DjangoがHTMLを返します。そのHTML内に埋め込まれたVite用のテンプレートタグが、**Vite開発サーバー（ポート5173）**を指すスクリプトタグを生成し、JavaScriptやCSS（Tailwindなど）を動的に読み込みます。これにより、コード変更時の即時反映（HMR: Hot Module Replacement）が可能になります。

本番環境では、Viteでビルドされた静的ファイル（ハッシュ付きファイル）を読み込むようになり、高速でキャッシュ効率の良いアセット配信が行われます。

---

## 2. Django側の設定解説

### `config/settings.py`

```python
INSTALLED_APPS = [
    # ...
    "othello_web",
    "django_vite", # django-vite アプリを登録
]

# Viteの設定
DJANGO_VITE_ASSETS_PATH = BASE_DIR / "othello_web" / "static" / "dist"
DJANGO_VITE_DEV_MODE = DEBUG
DJANGO_VITE_DEV_SERVER_PORT = 5173
```

- **`django_vite`**: Viteとの連携を管理するためのライブラリを有効化します。
- **`DJANGO_VITE_ASSETS_PATH`**: Viteがビルドしたファイル（本番用）が出力される絶対パスを指定します。ここに `manifest.json` が生成され、Djangoはそれを読み取ってファイルパスを解決します。
- **`DJANGO_VITE_DEV_MODE`**: `DEBUG` が `True` の場合は Vite の開発サーバーからアセットを読み込み（HMR有効）、`False` の場合はビルド済みの静的ファイルから読み込みます。
- **`DJANGO_VITE_DEV_SERVER_PORT`**: Vite開発サーバーのポート番号（デフォルトは 5173）を指定します。

### `othello_web/templates/base.html` (テンプレート側)

```html
{% load django_vite %}

<!-- 開発サーバー(Vite)との通信用HMRクライアント -->
{% vite_hmr_client %}

<!-- Viteでビルド・管理されるメインJS -->
{% vite_asset 'src/main.js' %}
```

- **`{% load django_vite %}`**: `django-vite` のカスタムテンプレートタグを読み込みます。
- **`{% vite_hmr_client %}`**: 開発モードでのみ、ViteのHMR用スクリプトを注入します（画面リロードなしで変更を反映させるため）。
- **`{% vite_asset 'src/main.js' %}`**: 指定したエントリーポイント（JSやCSS）を読み込む `<script>` や `<link>` タグを生成します。開発時は `http://localhost:5173/static/src/main.js` に、本番環境では `manifest.json` から解決したハッシュ付きファイルパスに変換されます。

---

## 3. Vite側の設定解説

### `frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [
    tailwindcss(),
  ],
  server: {
    port: 5173,
    open: false,
    cors: true, // Djangoからのリクエストを許可する
  },
  base: '/static/',
  build: {
    manifest: true,
    outDir: '../othello_web/static/dist', // Djangoの静的ファイルディレクトリに合わせて調整
    rollupOptions: {
      input: 'src/main.js', // エントリーポイント（JSかCSS）
    },
  },
});
```

- **`server.cors: true`**: Djangoサーバー（例: `localhost:8000`）からViteサーバー（`localhost:5173`）へのクロスオリジンリソースアクセス（CORS）を許可します。これがないとブラウザのセキュリティ制限でアセットが読み込めません。
- **`base: '/static/'`**: Viteが生成するアセットのベースURLを指定します。Djangoの `STATIC_URL` と一致させる必要があります。
- **`build.manifest: true`**: 本番ビルド時に `.vite/manifest.json`（または `manifest.json`）を出力します。これは元のファイル名とビルド後のハッシュ付きファイル名のマッピング辞書であり、`django-vite` が本番パスを解決するために必須です。
- **`build.outDir`**: ビルドされたファイルの出力先です。Django側の `DJANGO_VITE_ASSETS_PATH` と一致する場所に設定します。
- **`build.rollupOptions.input`**: ビルドの起点となるファイル（エントリーポイント）を指定します。

---

## 4. 今回の接続方法（django-vite）のメリット・デメリット

### メリット
1. **HMR（Hot Module Replacement）の恩恵**: 開発中、CSSやJavaScriptを変更すると画面全体をリロードせずに即座にブラウザに反映されるため、フロントエンドの開発体験が飛躍的に向上します。
2. **Djangoのエコシステムを活かせる**: Djangoの強力なテンプレートエンジン（`base.html` などの継承や `{% url %}` タグなど）をそのまま使いながら、モダンなフロントエンドツールを統合できます。
3. **本番環境の最適化**: ビルド時にハッシュ付きのファイル名になるため、ブラウザのキャッシュ制御が容易になり、Viteの強力な最適化（Minifyなど）の恩恵を受けられます。

### デメリット
1. **開発時のサーバーの複数起動**: Django（`python manage.py runserver`）とVite（`npm run dev`）の2つのプロセスを同時に立ち上げる必要があります。
2. **初期設定の複雑さ**: CORSの設定、パスの合わせ込み、`manifest.json` の連携など、DjangoとViteの両方の知識がないとトラブルシューティングが難しくなります。
3. **完全なSPAではない**: ページ遷移時は通常のDjangoによる画面遷移（サーバーサイドレンダリング）となるため、ReactやVueを使った完全なSPA（Single Page Application）のようなシームレスな遷移にはなりません。

---

## 5. 他の接続方法（代替案）

現在の `django-vite` を用いたテンプレート統合型以外の連携方法として、以下のようなアプローチがあります。

### A. 完全なSPAアーキテクチャ（API連携）
DjangoをバックエンドAPI（Django REST Framework や Django Ninja を使用）としてのみ機能させ、フロントエンド（React / Vue / Svelte）は独立してViteで構築する方法です。
- **仕組み**: ViteでビルドしたHTMLをNginx等でホスティングし、データ通信は全てJSONを用いたAPI経由で行います。
- **メリット**: フロントエンドとバックエンドが完全に分離され、モバイルアプリへの展開や開発の並行化が容易になります。
- **デメリット**: Djangoのテンプレート機能やセッション認証が使いづらくなり、JWTトークン認証などを自前で実装・管理する必要があります。

### B. 自作で Manifest をパースする手法（ライブラリ不使用）
`django-vite` などのライブラリを使わず、Viteが生成する `manifest.json` をDjangoのカスタムテンプレートタグで独自にパースする方法です。
- **仕組み**: PythonでJSONを読み込み、元のファイル名からハッシュ付きのパスを解決する処理を自作します。
- **メリット**: 外部ライブラリへの依存が減り、自由なカスタマイズが可能です。
- **デメリット**: HMRを機能させるための条件分岐や、エラーハンドリングなどをすべて自作する必要があります。

### C. リバースプロキシでのルーティング（Nginx / Docker使用）
開発環境で Nginx などのリバースプロキシを立て、同じポートでルーティングを分ける方法です。
- **仕組み**: 例えば `http://localhost/api` へのアクセスはDjangoへ、それ以外（`http://localhost/`）へのアクセスはViteの開発サーバーへ振り分けます。
- **メリット**: CORSの問題が発生せず、本番環境の構成に近い状態で開発できます。
- **デメリット**: Dockerなどのコンテナ技術やプロキシ設定の知識が必要で、インフラ構成の敷居が上がります。
