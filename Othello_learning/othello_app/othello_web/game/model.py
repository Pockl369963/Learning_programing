import torch
import torch.nn as nn
import torch.nn.functional as F

class SEResNetBlock(nn.Module):
    """Squeeze-and-Excitation を追加した ResNetブロック"""
    def __init__(self, in_channels, out_channels, reduction=16):
        super(SEResNetBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.gn1 = nn.GroupNorm(32, out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self.gn2 = nn.GroupNorm(32, out_channels)

        self.se_fc1 = nn.Linear(out_channels, out_channels // reduction, bias=False)
        self.se_fc2 = nn.Linear(out_channels // reduction, out_channels, bias=False)

    def forward(self, x):
        residual = x
        out = F.relu(self.gn1(self.conv1(x)))
        out = self.gn2(self.conv2(out))

        # SE Operation
        se = out.mean((2, 3)) 
        se = F.relu(self.se_fc1(se))
        se = torch.sigmoid(self.se_fc2(se))
        se = se.unsqueeze(2).unsqueeze(3)
        out = out * se 

        out += residual
        out = F.relu(out)
        return out
    

class QNetwork(nn.Module):
    def __init__(self, input_channels=3, output_dim=64, num_res_blocks=5, num_atoms=51):
        super().__init__()
        self.hidden_dim = 128
        self.output_dim = output_dim
        self.num_atoms = num_atoms
        
        self.conv_in = nn.Conv2d(input_channels, self.hidden_dim, kernel_size=3, padding=1, bias=False)
        self.gn_in = nn.GroupNorm(32, self.hidden_dim)
        
        blocks = [SEResNetBlock(self.hidden_dim, self.hidden_dim) for _ in range(num_res_blocks)]
        self.res_blocks = nn.Sequential(*blocks)
        
        # Advantage Head
        self.adv_conv = nn.Conv2d(self.hidden_dim, 2, kernel_size=1)
        self.adv_gn = nn.GroupNorm(1, 2)
        self.adv_fc = nn.Linear(2 * 8 * 8, output_dim * num_atoms)
        
        # Value Head
        self.val_conv = nn.Conv2d(self.hidden_dim, 1, kernel_size=1)
        self.val_gn = nn.GroupNorm(1, 1)
        self.val_fc1 = nn.Linear(1 * 8 * 8, 64)
        self.val_fc2 = nn.Linear(64, num_atoms)

    def forward(self, x):
        x = F.relu(self.gn_in(self.conv_in(x)))
        x = self.res_blocks(x)
        
        adv = F.relu(self.adv_gn(self.adv_conv(x)))
        adv = adv.view(adv.size(0), -1)
        adv = self.adv_fc(adv) 
        
        val = F.relu(self.val_gn(self.val_conv(x)))
        val = val.view(val.size(0), -1)
        val = F.relu(self.val_fc1(val))
        val = self.val_fc2(val) 
        
        adv = adv.view(-1, self.output_dim, self.num_atoms) # [B, 64, 51]
        val = val.view(-1, 1, self.num_atoms) # [B, 1, 51]
        
        q_logits = val + adv - adv.mean(dim=1, keepdim=True)
        return F.log_softmax(q_logits, dim=2)