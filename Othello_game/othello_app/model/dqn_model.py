import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import List


class SEResNetBlock(nn.Module):
    """Squeeze-and-Excitation を追加した ResNetブロック"""

    def __init__(
        self, in_channels: int, out_channels: int, reduction: int = 16
    ) -> None:
        super(SEResNetBlock, self).__init__()
        self.conv1: nn.Conv2d = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, padding=1, bias=False
        )
        self.gn1: nn.GroupNorm = nn.GroupNorm(32, out_channels)
        self.conv2: nn.Conv2d = nn.Conv2d(
            out_channels, out_channels, kernel_size=3, padding=1, bias=False
        )
        self.gn2: nn.GroupNorm = nn.GroupNorm(32, out_channels)

        self.se_fc1: nn.Linear = nn.Linear(
            out_channels, out_channels // reduction, bias=False
        )
        self.se_fc2: nn.Linear = nn.Linear(
            out_channels // reduction, out_channels, bias=False
        )

    def forward(self, x: Tensor) -> Tensor:
        residual: Tensor = x
        out: Tensor = F.relu(self.gn1(self.conv1(x)))
        out = self.gn2(self.conv2(out))

        # SE Operation
        se: Tensor = out.mean((2, 3))
        se = F.relu(self.se_fc1(se))
        se = torch.sigmoid(self.se_fc2(se))
        se = se.unsqueeze(2).unsqueeze(3)
        out = out * se

        out += residual
        out = F.relu(out)
        return out


class QNetwork(nn.Module):
    def __init__(
        self,
        input_channels: int = 3,
        output_dim: int = 64,
        num_res_blocks: int = 5,
        num_atoms: int = 51,
    ) -> None:
        super().__init__()
        self.hidden_dim: int = 128
        self.output_dim: int = output_dim
        self.num_atoms: int = num_atoms

        self.conv_in: nn.Conv2d = nn.Conv2d(
            input_channels, self.hidden_dim, kernel_size=3, padding=1, bias=False
        )
        self.gn_in: nn.GroupNorm = nn.GroupNorm(32, self.hidden_dim)

        blocks: List[nn.Module] = [
            SEResNetBlock(self.hidden_dim, self.hidden_dim)
            for _ in range(num_res_blocks)
        ]
        self.res_blocks: nn.Sequential = nn.Sequential(*blocks)

        # Advantage Head
        self.adv_conv: nn.Conv2d = nn.Conv2d(self.hidden_dim, 2, kernel_size=1)
        self.adv_gn: nn.GroupNorm = nn.GroupNorm(1, 2)
        self.adv_fc: nn.Linear = nn.Linear(2 * 8 * 8, output_dim * num_atoms)

        # Value Head
        self.val_conv: nn.Conv2d = nn.Conv2d(self.hidden_dim, 1, kernel_size=1)
        self.val_gn: nn.GroupNorm = nn.GroupNorm(1, 1)
        self.val_fc1: nn.Linear = nn.Linear(1 * 8 * 8, 64)
        self.val_fc2: nn.Linear = nn.Linear(64, num_atoms)

    def forward(self, x: Tensor) -> Tensor:
        x = F.relu(self.gn_in(self.conv_in(x)))
        x = self.res_blocks(x)

        adv: Tensor = F.relu(self.adv_gn(self.adv_conv(x)))
        adv = adv.view(adv.size(0), -1)
        adv = self.adv_fc(adv)

        val: Tensor = F.relu(self.val_gn(self.val_conv(x)))
        val = val.view(val.size(0), -1)
        val = F.relu(self.val_fc1(val))
        val = self.val_fc2(val)

        adv = adv.view(-1, self.output_dim, self.num_atoms)  # [B, 64, 51]
        val = val.view(-1, 1, self.num_atoms)  # [B, 1, 51]

        q_logits: Tensor = val + adv - adv.mean(dim=1, keepdim=True)
        return F.log_softmax(q_logits, dim=2)
