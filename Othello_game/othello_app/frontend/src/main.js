import './style.css';
import { fetchWithCSRF } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    const testBtn = document.getElementById('csrf-test-btn');
    const resultDiv = document.getElementById('csrf-test-result');

    if (testBtn && resultDiv) {
        testBtn.addEventListener('click', async () => {
            resultDiv.textContent = '通信中...';
            resultDiv.className = 'mt-4 p-3 bg-gray-50 rounded text-sm font-mono text-gray-700 min-h-[3rem]';

            try {
                // CSRF付きでDjangoのテストAPIを叩く
                const response = await fetchWithCSRF('/api/test-csrf/', {
                    method: 'POST',
                    body: JSON.stringify({ ping: 'pong' })
                });

                const data = await response.json();

                if (response.ok) {
                    resultDiv.textContent = `成功！🎉 ステータス: ${response.status}\nメッセージ: ${data.message}`;
                    resultDiv.className = 'mt-4 p-3 bg-green-100 rounded text-sm font-mono text-green-800 whitespace-pre-line min-h-[3rem] border border-green-300';
                } else {
                    resultDiv.textContent = `失敗... 😢 ステータス: ${response.status}\nエラー: ${data.error || '不明なエラー'}`;
                    resultDiv.className = 'mt-4 p-3 bg-red-100 rounded text-sm font-mono text-red-800 whitespace-pre-line min-h-[3rem] border border-red-300';
                }
            } catch (error) {
                resultDiv.textContent = `ネットワークエラー発生: ${error.message}`;
                resultDiv.className = 'mt-4 p-3 bg-red-100 rounded text-sm font-mono text-red-800 min-h-[3rem] border border-red-300';
            }
        });
    }
});
