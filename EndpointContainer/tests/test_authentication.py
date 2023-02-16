from unittest import TestCase, mock

from sqlalchemy import create_engine, MetaData

import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from factory import create_web_app
from Submissions import Submissions

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
        with self.app.app_context():
            # util.drop_all()
            # util.create_all()

            with util.transaction() as session:
                session.execute('PRAGMA foreign_keys = OFF;')
                metadata = MetaData()
                db_user = models.DBUser(
                    user_id=1,
                    first_name='first',
                    last_name='last',
                    suffix_name='iv',
                    email='first@last.iv',
                    policy_class=2,
                    flag_edit_users=1,
                    flag_email_verified=1,
                    flag_edit_system=0,
                    flag_approved=1,
                    flag_deleted=0,
                    flag_banned=0,
                    tracking_cookie='foocookie',
                )
                db_submission = Submissions(
                    submission_id = 12,
                    document_id = 1,
                    doc_paper_id = 1,
                    sword_id = None,
                    userinfo = None,
                    submitter_id = 12,
                    submitter_name = 'first',
                    submitter_email = 'first@gmail.com',
                    created = None,
                    updated = None,
                    status = 9, # Make 7 for checking publicity
                    sticky_status = 1,
                    submit_time = None,
                    release_time = None,
                    source_format = None,
                    source_flags = None,
                    has_pilot_data = 1,
                    title = 'Test Submission',
                    authors = 'first last',
                    comments = 'comments',
                    proxy = None,
                    report_num = None,
                    msc_class = None,
                    acm_class = None,
                    journal_ref = None,
                    doi = None,
                    abstract = 'This is the abstract',
                    license = None,
                    type = None,
                    is_ok = None,
                    admin_ok = 1,
                    rt_ticket_id = 1,
                )
                session.add(db_user)
                session.add(db_submission)

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
        _get_google_auth=mock.MagicMock(return_value=(None, None, None)), 
        _get_url=mock.MagicMock(return_value="test"))
    def test_logged_in_upload_good_sub(self, **mocks):
        """A logged in client for a submission they own"""
        mocks['_get_auth'].return_value = self.mock_auth
        client = self.app.test_client()
        resp = client.post('/upload', data={'submission_id' : 12})
        print (resp.status_code)
        assert resp.status_code == 200


    @mock.patch.multiple('routes', _get_auth=mock.DEFAULT, 
        _get_google_auth=mock.MagicMock(return_value=(None, None, None)), 
        _get_url=mock.MagicMock(return_value="test"))
    def test_logged_in_upload_bad_sub(self, **mocks):
        """A logged in client for a submission they do not own"""
        mocks['_get_auth'].return_value = self.mock_auth
        client = self.app.test_client()
        resp = client.post('/upload', data={'submission_id' : 11})
        print (resp.status_code)
        assert resp.status_code == 403
