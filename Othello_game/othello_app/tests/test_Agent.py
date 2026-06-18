import pytest
import numpy as np
from typing import List
from unittest.mock import patch, MagicMock

from model.Agent import AIPlayer
from model.othello_env import OthelloEnv


@pytest.fixture
def initial_board() -> List[List[int]]:
    """初期状態の盤面を提供するフィクスチャ。"""
    return OthelloEnv().get_initial_board()


@pytest.fixture
def agent() -> AIPlayer:
    """ランダムな重みで初期化されたAIPlayerを提供するフィクスチャ。"""
    # model_pathを指定しないことで、ランダムな重みで初期化される
    return AIPlayer()


class TestAIPlayer:
    """AIPlayer (Agent.py) のテストスイート"""

    def test_get_observation_initial(
        self, agent: AIPlayer, initial_board: List[List[int]]
    ) -> None:
        """正常系: 初期盤面からDQN入力用のObservationが正しく生成されること。"""
        # Act
        obs = agent._get_observation(
            initial_board, current_player=OthelloEnv.PLAYER_BLACK
        )

        # Assert
        # 全体のShapeが (3, 8, 8) であること
        assert obs.shape == (3, 8, 8)

        # チャンネル0 (自分の石: 1) の確認
        assert obs[0, 3, 4] == 1.0
        assert obs[0, 4, 3] == 1.0
        assert np.sum(obs[0]) == 2.0  # 黒石は2個だけ

        # チャンネル1 (相手の石: -1) の確認
        assert obs[1, 3, 3] == 1.0
        assert obs[1, 4, 4] == 1.0
        assert np.sum(obs[1]) == 2.0  # 白石は2個だけ

        # チャンネル2 (合法手) の確認
        # 初期配置での黒の合法手は (2,3), (3,2), (4,5), (5,4)
        assert obs[2, 2, 3] == 1.0
        assert obs[2, 3, 2] == 1.0
        assert obs[2, 4, 5] == 1.0
        assert obs[2, 5, 4] == 1.0
        assert np.sum(obs[2]) == 4.0  # 合法手は4箇所だけ

    def test_get_observation_white(
        self, agent: AIPlayer, initial_board: List[List[int]]
    ) -> None:
        """正常系: 白番(後手)の場合、チャンネル0が白石、チャンネル1が黒石として反転生成されること。"""
        # Act
        obs = agent._get_observation(
            initial_board, current_player=OthelloEnv.PLAYER_WHITE
        )

        # Assert
        # チャンネル0 (自分の石 = 白石: -1) の確認
        assert obs[0, 3, 3] == 1.0
        assert obs[0, 4, 4] == 1.0
        assert np.sum(obs[0]) == 2.0

        # チャンネル1 (相手の石 = 黒石: 1) の確認
        assert obs[1, 3, 4] == 1.0
        assert obs[1, 4, 3] == 1.0
        assert np.sum(obs[1]) == 2.0

        # チャンネル2 (合法手) の確認
        assert obs[2, 2, 4] == 1.0
        assert obs[2, 4, 2] == 1.0
        assert obs[2, 3, 5] == 1.0
        assert obs[2, 5, 3] == 1.0
        assert np.sum(obs[2]) == 4.0

    def test_get_move_returns_valid_move(
        self, agent: AIPlayer, initial_board: List[List[int]]
    ) -> None:
        """正常系: ネットワークの出力に関わらず、非合法手がマスクされて必ず合法手が選ばれること。"""
        # Arrange
        # ランダムな重みのモデルを使うため、Q値自体はデタラメになる。
        # しかし、AIPlayer側のマスキング処理によって、確実に合法手が選択されるはず。

        # Act
        move = agent.get_move(initial_board, current_player=OthelloEnv.PLAYER_BLACK)

        # Assert
        assert move is not None, "合法手が存在するのにNoneが返されました。"
        row, col = move

        # 選ばれた手が本当に合法手であるか検証
        assert agent.env.is_valid_move(
            initial_board, OthelloEnv.PLAYER_BLACK, row, col
        ), (
            f"非合法手 ({row}, {col}) が選ばれました。マスキング処理が正しく働いていません。"
        )

    def test_get_move_no_valid_moves(self, agent: AIPlayer) -> None:
        """正常系: 合法手がない場合はパスとなり、Noneを返すこと。"""
        # Arrange
        # 1箇所を除いて全て黒で埋まった盤面（相手を裏返せない状態）
        board = [[1] * 8 for _ in range(8)]
        board[0][0] = 0

        # Act
        # 白番(相手)のターン。空いている(0,0)に置いても裏返せる黒石がないので合法手は0。
        move = agent.get_move(board, current_player=OthelloEnv.PLAYER_WHITE)

        # Assert
        assert move is None, "合法手がない盤面で、None以外が返されました。"

    @patch("model.Agent.os.path.exists")
    @patch("model.Agent.torch.load")
    @patch("model.Agent.QNetwork.load_state_dict")
    def test_init_loads_model_path_with_mock(
        self,
        mock_load_state_dict: MagicMock,
        mock_torch_load: MagicMock,
        mock_path_exists: MagicMock,
    ) -> None:
        """正常系: model_pathが指定された場合、正しくロード処理(torch.load)が呼ばれること。"""
        # Arrange
        mock_path_exists.return_value = True
        mock_torch_load.return_value = {"online_net": "dummy_state_dict_data"}
        dummy_path = "dummy/path/to/best_model.pth"

        # Act
        # モックによりファイルが存在すると判定され、ロード処理が走る
        agent = AIPlayer(model_path=dummy_path)

        # Assert
        # 1. パスの存在確認が行われたか
        mock_path_exists.assert_called_once_with(dummy_path)
        # 2. torch.load が正しいパスとデバイス指定で呼ばれたか
        mock_torch_load.assert_called_once_with(dummy_path, map_location=agent.device)
        # 3. ネットワークに辞書の 'online_net' の中身がロードされたか
        mock_load_state_dict.assert_called_once_with("dummy_state_dict_data")

    @patch("model.Agent.os.path.exists")
    @patch("model.Agent.torch.load")
    def test_init_load_failure_fallback(
        self, mock_torch_load: MagicMock, mock_path_exists: MagicMock
    ) -> None:
        """異常系: torch.loadで例外が発生した場合、クラッシュせずにランダムな重みで初期化が継続されること。"""
        # Arrange
        mock_path_exists.return_value = True
        # ロード中に例外が発生した状況をシミュレート
        mock_torch_load.side_effect = RuntimeError("Mocked corrupted file error")
        dummy_path = "dummy/path/to/corrupted_model.pth"

        # Act & Assert
        try:
            # 例外が送出されず、キャッチされてインスタンス化が進むことを確認
            agent = AIPlayer(model_path=dummy_path)
        except Exception as e:
            pytest.fail(
                f"ロード失敗時に例外がスローされ、アプリがクラッシュしました: {e}"
            )

        # Agentと内部ネットワークが生成されていることを確認
        assert agent is not None
        assert agent.net is not None
