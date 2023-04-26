"""Auth unit tests"""
import sys
import os
from unittest import TestCase, mock
from arxiv_auth import domain
from arxiv_auth.legacy import exceptions, util, models
from factory import create_web_app

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))

class TestAuthenticationController(TestCase):
    """
    Test class for testing auth

    Parameters
    ----------
    TestCase : unittest.TestCase
    """
    def setUp(self):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
        self.app = create_web_app('tests/config.py')
        self.mock_auth = mock.MagicMock()
        self.mock_user = mock.MagicMock()
        self.mock_user.user_id = 12
        self.mock_auth.user = self.mock_user

    @mock.patch.multiple('routes', _get_auth=mock.DEFAULT, _get_google_auth=mock.DEFAULT)
    def test_unauth_download(self, **mocks):
        """A non logged in client gets rejected"""
        mocks['_get_auth'].return_value = None
        client = self.app.test_client()
        resp = client.get('/download')
        assert resp.status_code == 403

    @mock.patch.multiple('routes', _get_auth=mock.DEFAULT, _get_google_auth=mock.DEFAULT)
    def test_unauth_upload(self, **mocks):
        """A non logged in client gets rejected"""
        mocks['_get_auth'].return_value = None
        client = self.app.test_client()
        resp = client.post('/upload')
        assert resp.status_code == 403


    @mock.patch.multiple('routes', _get_auth=mock.DEFAULT,
        _get_google_auth=mock.MagicMock(return_value=(None, None, None)), _get_url=mock.MagicMock(return_value="test"))
    def test_logged_in_upload_good_sub(self, **mocks):
        """A logged in client for a submission they own"""
        mocks['_get_auth'].return_value = self.mock_auth
        client = self.app.test_client()
        resp = client.post('/upload', data={'submission_id' : 12})
        print (resp.status_code)
        assert resp.status_code == 200


    @mock.patch.multiple('routes', _get_auth=mock.DEFAULT,
        _get_google_auth=mock.MagicMock(return_value=(None, None, None)), _get_url=mock.MagicMock(return_value="test"))
    def test_logged_in_upload_bad_sub(self, **mocks):
        """A logged in client for a submission they do not own"""
        mocks['_get_auth'].return_value = self.mock_auth
        client = self.app.test_client()
        resp = client.post('/upload', data={'submission_id' : 11})
        print (resp.status_code)
        assert resp.status_code == 403
