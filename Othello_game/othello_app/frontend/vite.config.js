import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  plugins: [
    tailwindcss(), // ここでプラグインを有効化します
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