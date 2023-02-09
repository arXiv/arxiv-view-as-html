from unittest import TestCase, mock
from factory import create_web_app

from arxiv_auth import domain
from arxiv_auth.legacy import exceptions, util, models


class TestAuthenticationController(TestCase):

    def setUp(self):
        self.app = create_web_app('tests/config.py')

    @mock.patch('routes._get_auth')
    def test_unauth_download(self, mock_get_auth):
        """A non logged in client gets rejected"""
        mock_get_auth.return_value = None
        client = self.app.test_client()
        resp = client.get('/download')
        assert resp.status_code == 403


    @mock.patch('routes._get_auth')
    def test_unauth_upload(self, mock_get_auth):
        """A non logged in client gets rejected"""
        mock_get_auth.return_value = None
        client = self.app.test_client()
        resp = client.post('/upload')
        assert resp.status_code == 403


    @mock.patch('routes._get_auth')
    def test_logged_in_upload_good_sub(self, mock_get_auth):
        """A logged in client for a submission they own"""
        # TODO
        pass


    @mock.patch('routes._get_auth')
    def test_logged_in_upload_bad_sub(self, mock_get_auth):
        """A logged in client for a submission they do not own"""
        # TODO
        pass
