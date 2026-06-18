import torch
import numpy as np
import os
from typing import Optional, Tuple, Any, List
from numpy.typing import NDArray

from .dqn_model import QNetwork
from .othello_env import OthelloEnv


class AIPlayer:
    def __init__(self, model_path: Optional[str] = None) -> None:
        self.device: torch.device = torch.device("cpu")
        self.net: QNetwork = QNetwork().to(self.device)
        self.net.eval()
        self.env = OthelloEnv()

        if model_path and os.path.exists(model_path):
            try:
                checkpoint: Any = torch.load(
                    model_path, map_location=self.device, weights_only=True
                )
                if isinstance(checkpoint, dict) and "online_net" in checkpoint:
                    self.net.load_state_dict(checkpoint["online_net"])
                else:
                    self.net.load_state_dict(checkpoint)
                print(f"AI loaded model from {model_path}")
            except Exception as e:
                print(f"Failed to load AI model: {e}")
        else:
            print("AI initialized with random weights")

    def _get_observation(
        self, board: List[List[int]], current_player: int
    ) -> NDArray[np.float32]:
        """
        現在の盤面とプレイヤーからDQNモデルに入力するObservation (3x8x8) を生成します。
        チャンネル0: 自分の石 (1.0 or 0.0)
        チャンネル1: 相手の石 (1.0 or 0.0)
        チャンネル2: 合法手 (1.0 or 0.0)
        """
        obs: NDArray[np.float32] = np.zeros((3, 8, 8), dtype=np.float32)
        opponent = (
            self.env.PLAYER_WHITE
            if current_player == self.env.PLAYER_BLACK
            else self.env.PLAYER_BLACK
        )

        for r in range(8):
            for c in range(8):
                cell = board[r][c]
                if cell == current_player:
                    obs[0, r, c] = 1.0
                elif cell == opponent:
                    obs[1, r, c] = 1.0

                # 合法手チェック
                if cell == self.env.EMPTY and self.env.is_valid_move(
                    board, current_player, r, c
                ):
                    obs[2, r, c] = 1.0

        return obs

    def get_move(
        self, board: List[List[int]], current_player: int
    ) -> Optional[Tuple[int, int]]:
        obs: NDArray[np.float32] = self._get_observation(board, current_player)

        legal_moves_mask: NDArray[np.float32] = obs[2].flatten()
        legal_indices: NDArray[np.int64] = np.where(legal_moves_mask == 1)[0]

        if len(legal_indices) == 0:
            return None

        state: torch.Tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)

        with torch.no_grad():
            q_log_probs: torch.Tensor = self.net(state)

        q_probs: torch.Tensor = torch.exp(q_log_probs)

        # C51サポート値
        V_MIN: float = -1.4
        V_MAX: float = 1.4
        NUM_ATOMS: int = 51
        support: torch.Tensor = torch.linspace(V_MIN, V_MAX, NUM_ATOMS).to(self.device)

        # 期待値計算
        q_values_tensor: torch.Tensor = (q_probs * support).sum(dim=2)
        q_values: NDArray[np.float32] = q_values_tensor.cpu().numpy().flatten()

        # 【重要】合法手以外をマスクしてルール違反を防ぐ
        masked_q_values: NDArray[np.float32] = np.where(
            legal_moves_mask == 1, q_values, -1e10
        )
        best_action_idx: int = int(np.argmax(masked_q_values))

        row: int = best_action_idx // 8
        col: int = best_action_idx % 8

        return row, col
