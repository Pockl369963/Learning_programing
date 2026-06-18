import torch

from model.dqn_model import QNetwork


class TestQNetwork:
    """QNetworkのテストスイート"""

    def test_forward_shape(self) -> None:
        """正常系: (1, 3, 8, 8)のダミー入力に対して、(1, 64, 51)の出力が返ることの健全性(Sanity)チェック。"""
        # Arrange
        model = QNetwork()
        model.eval()
        # バッチサイズ1、チャンネル3(自石, 相手石, 合法手)、8x8の盤面
        dummy_input = torch.randn(1, 3, 8, 8)

        # Act
        with torch.no_grad():
            output = model(dummy_input)

        # Assert
        # 期待される出力Shape: (Batch, output_dim, num_atoms) = (1, 64, 51)
        assert output.shape == (1, 64, 51)
        # 異常な値(NaN)が含まれていないことの確認
        assert not torch.isnan(output).any(), "出力にNaNが含まれています。"
