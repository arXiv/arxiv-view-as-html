from unittest import TestCase, mock

import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from factory import create_web_app

from arxiv_auth import domain
from arxiv_auth.legacy import exceptions, util, models


class TestAuthenticationController(TestCase):

    def setUp(self):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
        self.app = create_web_app('tests/config.py')
        self.mock_auth = mock.MagicMock()
        self.mock_user = mock.MagicMock()
        self.mock_user.user_id = 12
        self.mock_auth.user = self.mock_user