import torch
import numpy as np
import os
from .model import QNetwork
from .engine import OthelloGame

class AIPlayer:
    def __init__(self, model_path=None):
        self.device = torch.device("cpu")
        self.net = QNetwork().to(self.device)
        self.net.eval()
        
        if model_path and os.path.exists(model_path):
            try:
                checkpoint = torch.load(model_path, map_location=self.device)
                if 'online_net' in checkpoint:
                    self.net.load_state_dict(checkpoint['online_net'])
                else:
                    self.net.load_state_dict(checkpoint)
                print(f"AI loaded model from {model_path}")
            except Exception as e:
                print(f"Failed to load AI model: {e}")
        else:
            print("AI initialized with random weights")

    def get_move(self, game: OthelloGame):
        player = game.current_player
        obs = game.get_observation(player)
        
        legal_moves_mask = obs[2].flatten()
        legal_indices = np.where(legal_moves_mask == 1)[0]
        
        if len(legal_indices) == 0:
            return None

        state = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            q_log_probs = self.net(state)
        
        q_probs = torch.exp(q_log_probs)
        
        # C51サポート値
        V_MIN, V_MAX, NUM_ATOMS = -1.4, 1.4, 51
        support = torch.linspace(V_MIN, V_MAX, NUM_ATOMS).to(self.device)
        
        # 期待値計算
        q_values = (q_probs * support).sum(dim=2)
        q_values = q_values.cpu().numpy().flatten()
        
        # 【重要】合法手以外をマスクしてルール違反を防ぐ
        masked_q_values = np.where(legal_moves_mask == 1, q_values, -1e10)
        best_action_idx = np.argmax(masked_q_values).item()
        
        row = best_action_idx // 8
        col = best_action_idx % 8
        
        return row, col