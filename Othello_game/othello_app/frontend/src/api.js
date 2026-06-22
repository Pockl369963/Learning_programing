// CSRFトークンを取得するヘルパー関数
export function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
        return meta.getAttribute('content');
    }
    console.warn("CSRFトークンが見つかりません。base.htmlに <meta name='csrf-token'> が設定されているか確認してください。");
    return '';
}

/**
 * CSRFトークンを自動的に付与するFetch APIのラッパー関数
 * @param {string} url - リクエスト先のURL
 * @param {Object} options - fetchのオプション
 * @returns {Promise<Response>}
 */
export async function fetchWithCSRF(url, options = {}) {
    const csrfToken = getCsrfToken();
    
    // optionsが未定義またはヘッダーが未定義の場合は初期化
    const fetchOptions = { ...options };
    fetchOptions.headers = { ...fetchOptions.headers };

    // CSRFトークンをヘッダーにセット（Djangoが要求する 'X-CSRFToken' ヘッダー）
    if (csrfToken) {
        fetchOptions.headers['X-CSRFToken'] = csrfToken;
    }

    // メソッドが指定されていない場合はGETとする
    const method = fetchOptions.method ? fetchOptions.method.toUpperCase() : 'GET';

    // POST, PUT, PATCH, DELETE等の場合でContent-Typeが未指定、かつFormDataではない場合はJSONとする
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        if (!fetchOptions.headers['Content-Type'] && !(fetchOptions.body instanceof FormData)) {
            fetchOptions.headers['Content-Type'] = 'application/json';
        }
    }

    // クッキーなどの情報を同一オリジンで送受信するための設定
    if (!fetchOptions.credentials) {
        fetchOptions.credentials = 'same-origin';
    }

    return fetch(url, fetchOptions);
}
