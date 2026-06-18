import torch

from model.dqn_model import QNetwork


class TestQNetwork:
    """QNetworkのテストスイート"""

    def test_forward_shape(self) -> None:
        """
        [正常系] (1, 3, 8, 8)のダミー入力に対して、(1, 64, 51)の出力が返ることの健全性(Sanity)チェック。

        Arrange:
            QNetworkモデルを初期化し、評価モード(eval)にする。
            バッチサイズ1、チャンネル3(自石, 相手石, 合法手)、8x8の盤面を表すダミーテンソルを用意する。
        Act:
            モデルにダミーテンソルを入力し、推論(forward)を行う。
        Assert:
            - 出力テンソルのShapeが (Batch, output_dim, num_atoms) = (1, 64, 51) であること。
            - 出力テンソル内に異常な値(NaN)が含まれていないこと。
        """
        # Arrange
        model = QNetwork()
        model.eval()
        dummy_input = torch.randn(1, 3, 8, 8)

        # Act
        with torch.no_grad():
            output = model(dummy_input)

        # Assert
        assert output.shape == (1, 64, 51)
        assert not torch.isnan(output).any(), "出力にNaNが含まれています。"
