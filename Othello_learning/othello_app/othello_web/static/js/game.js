document.addEventListener('DOMContentLoaded', () => {
    const boardElement = document.getElementById('board');
    const statusElement = document.getElementById('status-message');
    const scoreBlackElement = document.getElementById('score-black');
    const scoreWhiteElement = document.getElementById('score-white');
    const btnReset = document.getElementById('btn-reset');

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.content : "";

    let isProcessing = false;
    let currentBoard = [];

    function updateStatus(msg) {
        statusElement.textContent = msg;
    }

    resetGame()

    btnReset.addEventListener('click', () => {
        resetGame();
    });

    async function resetGame() {
        if (isProcessing) return;
        isProcessing = true;
        updateStatus("Initializing...");

        try {
            const response = await fetch('/api/reset');
            const data = await response.json();
            renderBoard(data);
        } catch (error) {
            console.error('Error:', error);
            updateStatus("Error initializing game.");
        } finally {
            isProcessing = false;
        }
    }

    async function makeMove(row, col) {
        if (isProcessing) return; // 二重送信防止

        isProcessing = true;
        updateStatus("Thinking...");

        try {
            // 1. 人間の手を送信
            const response = await fetch('/api/move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ row, col })
            });
            const data = await response.json();

            if (data.valid === false) {
                updateStatus("Invalid move!");
                setTimeout(() => updateStatus("Your Turn (Black)"), 1000);
                isProcessing = false;
                return;
            }

            // 人間の手の結果をアニメーション描画
            await animateBoardUpdate(data.board);
            renderBoard(data); // 人間の手によるスコア更新や終了判定を反映

            // 2. AIのターンを処理（人間がパスになった場合の連続ターンに対応）
            let currentState = data;
            
            while (!currentState.is_done && currentState.current_player === -1) {
                // AIの思考時間として少し待機
                updateStatus("AI Thinking... (White)");
                await new Promise(r => setTimeout(r, 1000));

                const aiResponse = await fetch('/api/ai-move');
                if (aiResponse.ok) {
                    currentState = await aiResponse.json();
                    // AIの手の結果をアニメーション描画
                    await animateBoardUpdate(currentState.board);
                    renderBoard(currentState);
                } else {
                    break; // エラー時はループを抜ける
                }
            }

        } catch (error) {
            console.error('Error:', error);
            updateStatus("Error processing turn.");
        } finally {
            isProcessing = false;
        }
    }

    

    function renderBoard(data) {
        currentBoard = data.board;
        drawGrid(currentBoard);

        scoreBlackElement.textContent = data.black_count;
        scoreWhiteElement.textContent = data.white_count;

        if (data.is_done) {
            if (data.winner === -1) updateStatus("Game Over - White(AI) Wins!");
            else if (data.winner === 1) updateStatus("Game Over - Black(You) Win!");
            else updateStatus("Game Over - Draw!");
        } else {
            if (data.current_player === 1) updateStatus("Your Turn (Black)");
            else updateStatus("AI Thinking... (White)");
        }
    }

    function drawGrid(board) {
        boardElement.innerHTML = '';
        board.forEach((row, rS) => {
            row.forEach((cell, cS) => {
                const div = document.createElement('div');
                div.className = 'w-full h-full bg-green-600 flex items-center justify-center rounded-sm cursor-pointer hover:bg-green-500 transition relative';

                if (cell !== 0) {
                    const piece = document.createElement('div');
                    piece.className = `w-4/5 h-4/5 rounded-full shadow-lg transition-transform duration-500 transform`;
                    piece.style.backgroundColor = cell === 1 ? 'black' : 'white';
                    piece.id = `piece-${rS}-${cS}`;
                    div.appendChild(piece);
                }

                div.addEventListener('click', () => {
                    if (!isProcessing) makeMove(rS, cS);
                });
                boardElement.appendChild(div);
            });
        });
    }

    async function animateBoardUpdate(newBoard) {
        const diffs = [];
        let placedPiece = null;

        // 変化のあったマスを特定
        for (let r = 0; r < 8; r++) {
            for (let c = 0; c < 8; c++) {
                const oldVal = currentBoard[r] ? currentBoard[r][c] : 0;
                const newVal = newBoard[r][c];
                if (oldVal !== newVal) {
                    if (oldVal === 0) placedPiece = { r, c, val: newVal };
                    else diffs.push({ r, c, val: newVal });
                }
            }
        }

        // 1. 石を置く（古い盤面に新しい石だけ追加して描画）
        const tempBoard = JSON.parse(JSON.stringify(currentBoard));
        if (placedPiece) tempBoard[placedPiece.r][placedPiece.c] = placedPiece.val;
        drawGrid(tempBoard);
        await new Promise(r => setTimeout(r, 100)); // 描画を待つ

        // 置いた石からの距離でソート（近い順に裏返す）
        if (placedPiece) {
            diffs.sort((a, b) => {
                const distA = Math.max(Math.abs(a.r - placedPiece.r), Math.abs(a.c - placedPiece.c));
                const distB = Math.max(Math.abs(b.r - placedPiece.r), Math.abs(b.c - placedPiece.c));
                return distA - distB;
            });
        }

        // 2. 順番に裏返すアニメーション
        for (const diff of diffs) {
            const p = document.getElementById(`piece-${diff.r}-${diff.c}`);
            if (p) {
                p.style.transform = "scaleX(0)"; // 縮小
                await new Promise(r => setTimeout(r, 200));

                p.style.backgroundColor = (diff.val == 1) ? 'black' : 'white';
                
                p.style.transform = "scaleX(1)"; // 拡大
                await new Promise(r => setTimeout(r, 200));
            }
        }
        currentBoard = newBoard;
    }


});