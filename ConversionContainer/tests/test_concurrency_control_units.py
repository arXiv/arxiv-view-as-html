import pytest
from unittest.mock import MagicMock
from typing import Optional, Any
from flask_sqlalchemy.query import Query
import os
import logging

from ..conversion.factory import create_web_app
from ..conversion.models.util import (
    create_all,
    drop_all,
    transaction,
    now
)
from ..conversion.models.db import DBLaTeXMLDocuments, DBLaTeXMLSubmissions
from ..conversion.concurrency_control import write_start, write_success

from time import sleep

@pytest.fixture(autouse=True)
def change_test_dir(request, monkeypatch):
    monkeypatch.chdir(request.fspath.dirname)

@pytest.fixture
def app():
    app = create_web_app('tests/config.py')
    with app.app_context():
        drop_all()
        create_all()
    return app

@pytest.fixture
def insert_into_sub():
    def insert(sub_id: int, conversion_status: int,
               latexml_version: str, tex_checksum: str,
               conversion_start_time: int,
               conversion_end_time: Optional[int] = None) -> bool:
        with transaction() as session:
            session.add(
                DBLaTeXMLSubmissions(
                    submission_id=sub_id,
                    conversion_status=conversion_status,
                    latexml_version=latexml_version,
                    tex_checksum=tex_checksum,
                    conversion_start_time=conversion_start_time,
                    conversion_end_time=conversion_end_time
                )
            )
    return insert

@pytest.fixture
def select_from_sub():
    def select(sub_id: int) -> Optional[Query]:
        with transaction() as session:
            return session.query(DBLaTeXMLSubmissions) \
                .filter(DBLaTeXMLSubmissions.submission_id == sub_id) \
                .first()
    return select

@pytest.fixture
def insert_into_doc():
    def insert(paper_id: str, document_version: int, 
               conversion_status: int, latexml_version: str, 
               tex_checksum: str,
               conversion_start_time: int,
               conversion_end_time: Optional[int] = None) -> bool:
        with transaction() as session:
            session.add(
                DBLaTeXMLDocuments(
                    paper_id=paper_id,
                    document_version=document_version,
                    conversion_status=conversion_status,
                    latexml_version=latexml_version,
                    tex_checksum=tex_checksum,
                    conversion_start_time=conversion_start_time,
                    conversion_end_time=conversion_end_time
                )
            )
    return insert

@pytest.fixture
def select_from_doc():
    def select(paper_id: str, document_version: int) -> Optional[Query]:
        with transaction() as session:
            return session.query(DBLaTeXMLDocuments) \
                .filter(DBLaTeXMLDocuments.paper_id == paper_id) \
                .filter(DBLaTeXMLDocuments.document_version == document_version) \
                .first()
    return select


"""
******************************
***** write_start tests ******
******************************
"""

@pytest.mark.cc_unit_tests
def test_write_start_sub_simple (app, select_from_sub):
    assert os.path.exists('ancillary_files/3966840.tar.gz'), \
        'This test depends on tests/ancillary_files/3966840.tar.gz'
    with app.app_context():
        write_start(1, 'ancillary_files/3966840.tar.gz')

        row: Optional[Query] = select_from_sub(1)
        assert row is not None, 'Failed to write row'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '7fba16945d97c8828f6f7c255bd1ab10', \
            f'Incorrect checksum: {row.tex_checksum}'
        
@pytest.mark.cc_unit_tests
def test_write_start_sub_overlap (app, select_from_sub):
    assert os.path.exists('ancillary_files/3966840.tar.gz'), \
        'This test depends on tests/ancillary_files/3966840.tar.gz'
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        write_start(1, 'ancillary_files/2012.02205.tar.gz')
        old_ts = select_from_sub(1).conversion_start_time
        sleep(1)
        write_start(1, 'ancillary_files/3966840.tar.gz')

        row: Optional[Query] = select_from_sub(1)
        assert row is not None, 'Failed to write row'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '7fba16945d97c8828f6f7c255bd1ab10', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_start_time > old_ts, \
            f'Start timestamp is not later on second write: \
            {row.conversion_start_time} ≯ {old_ts}'

@pytest.mark.cc_unit_tests
def test_write_start_doc_no_version_simple (app, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        write_start('2012.02205', 'ancillary_files/2012.02205.tar.gz')

        row: Query = select_from_doc('2012.02205', 1)
        assert row is not None, 'Failed to write row'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        
@pytest.mark.cc_unit_tests
def test_write_start_doc_with_version_simple (app, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        write_start('2012.02205v2', 'ancillary_files/2012.02205.tar.gz')

        row: Optional[Query] = select_from_doc('2012.02205', 2)
        assert row is not None, 'Failed to write row'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        
@pytest.mark.cc_unit_tests
def test_write_start_doc_multiple_versions (app, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        write_start('2012.02205', 'ancillary_files/2012.02205.tar.gz')
        write_start('2012.02205v2', 'ancillary_files/3966840.tar.gz') 

        row_v1: Optional[Query] = select_from_doc('2012.02205', 1)
        assert row_v1 is not None, 'Failed to write row'
        assert row_v1.conversion_status == 0, \
            f'Incorrect conversion_status \'{row_v1.conversion_status}\' should be 0'
        assert row_v1.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row_v1.tex_checksum}'
        
        row_v2: Optional[Query] = select_from_doc('2012.02205', 2)
        assert row_v2 is not None, 'Failed to write row'
        assert row_v2.conversion_status == 0, \
            f'Incorrect conversion_status \'{row_v2.conversion_status}\' should be 0'
        assert row_v2.tex_checksum == '7fba16945d97c8828f6f7c255bd1ab10', \
            f'Incorrect checksum: {row_v2.tex_checksum}'
        
@pytest.mark.cc_unit_tests
def test_write_start_doc_overlap (app, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        write_start('2012.02205', 'ancillary_files/2012.02205.tar.gz')
        old_ts = select_from_doc('2012.02205', 1).conversion_start_time
        sleep(1)
        write_start('2012.02205v1', 'ancillary_files/3966840.tar.gz')

        row: Optional[Query] = select_from_doc('2012.02205', 1)
        assert row is not None, 'Failed to write row'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '7fba16945d97c8828f6f7c255bd1ab10', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_start_time > old_ts, \
            f'Start timestamp is not later on second write: \
            {row.conversion_start_time} ≯ {old_ts}'
        
@pytest.mark.cc_unit_tests
def test_write_start_doc_overlap_with_version (app, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():        
        write_start('2012.02205v3', 'ancillary_files/2012.02205.tar.gz')
        old_ts = select_from_doc('2012.02205', 3).conversion_start_time
        sleep(1)
        write_start('2012.02205v3', 'ancillary_files/3966840.tar.gz')

        row: Optional[Query] = select_from_doc('2012.02205', 3)
        assert row is not None, 'Failed to write row'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '7fba16945d97c8828f6f7c255bd1ab10', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_start_time > old_ts, \
            f'Start timestamp is not later on second write: \
            {row.conversion_start_time} ≯ {old_ts}'
        


"""
******************************
****  write_success tests ****
******************************
"""

@pytest.mark.cc_unit_tests
def test_write_success_sub_simple (app, insert_into_sub, select_from_sub):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        insert_into_sub (
            sub_id=1,
            conversion_status=0,
            latexml_version=app.config['LATEXML_COMMIT'],
            tex_checksum='5a67f1a2f9b1b436f2bd604e0131cf3a',
            conversion_start_time=now()
        )
        sleep(1)

        result = write_success(1, 'ancillary_files/2012.02205.tar.gz')

        row: Optional[Query] = select_from_sub (1)
        assert row is not None, 'Insert failed to write. Check test db configuration'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time is not None, \
            'Conversion end time not written'
        assert row.conversion_end_time > row.conversion_start_time, \
            f'End timestamp is not later than start: \
            {row.conversion_end_time} ≯ {row.conversion_start_time}'
        assert result, 'write_success should return True'
        
@pytest.mark.cc_unit_tests
def test_write_success_sub_overlap (app, insert_into_sub, select_from_sub):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    assert os.path.exists('ancillary_files/3966840.tar.gz'), \
        'This test depends on tests/ancillary_files/3966840.tar.gz'
    with app.app_context():
        insert_into_sub (
            sub_id=1,
            conversion_status=0,
            latexml_version=app.config['LATEXML_COMMIT'],
            tex_checksum='5a67f1a2f9b1b436f2bd604e0131cf3a',
            conversion_start_time=now()
        )
        sleep(1)

        # Emulate old version being written while new is still processing
        old_version_result = write_success(1, 'ancillary_files/3966840.tar.gz')
        sleep(1)

        row: Optional[Query] = select_from_sub (1)
        assert row is not None, 'Insert failed to write. Check test db configuration'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time is None, \
            f'Conversion end time was erroneously written: {row.conversion_end_time}'
        assert not old_version_result, 'write_success should return False'

        # Now new version finishes processing
        new_version_result = write_success(1, 'ancillary_files/2012.02205.tar.gz')

        row: Optional[Query] = select_from_sub (1)
        assert row is not None, 'Row is None'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time is not None, \
            'Conversion end time not written'
        assert row.conversion_end_time > row.conversion_start_time, \
            f'End timestamp is not later than start: \
            {row.conversion_end_time} ≯ {row.conversion_start_time}'
        assert new_version_result, 'write_success should return True'

@pytest.mark.cc_unit_tests
def test_write_success_sub_overlap_out_of_order (app, insert_into_sub, select_from_sub):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    assert os.path.exists('ancillary_files/3966840.tar.gz'), \
        'This test depends on tests/ancillary_files/3966840.tar.gz'
    with app.app_context():
        insert_into_sub (
            sub_id=1,
            conversion_status=0,
            latexml_version=app.config['LATEXML_COMMIT'],
            tex_checksum='5a67f1a2f9b1b436f2bd604e0131cf3a',
            conversion_start_time=now()
        )
        sleep(1)

        # Emulate new version beating the old version through the system
        new_version_result = write_success(1, 'ancillary_files/2012.02205.tar.gz')
        sleep(1)

        row: Optional[Query] = select_from_sub (1)
        end_time = row.conversion_end_time
        assert row is not None, 'Insert failed to write. Check test db configuration'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert end_time is not None, \
            'Conversion end time not written'
        assert end_time > row.conversion_start_time, \
            f'End timestamp is not later than start: \
            {end_time} ≯ {row.conversion_start_time}'
        assert new_version_result, 'write_success should return True'
        
        # Now new version finishes processing
        old_version_result = write_success(1, 'ancillary_files/3966840.tar.gz')

        row: Optional[Query] = select_from_sub (1)
        assert row is not None, 'Row is None'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time == end_time, \
            f'Conversion end time was rewritten. Expected {end_time} but \
            got {row.conversion_end_time}'
        assert not old_version_result, 'write_success should return False'


@pytest.mark.cc_unit_tests
def test_write_success_doc_simple (app, insert_into_doc, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    with app.app_context():
        insert_into_doc (
            paper_id='2012.02205',
            document_version=1,
            conversion_status=0,
            latexml_version=app.config['LATEXML_COMMIT'],
            tex_checksum='5a67f1a2f9b1b436f2bd604e0131cf3a',
            conversion_start_time=now()
        )
        sleep(1)

        result = write_success('2012.02205', 'ancillary_files/2012.02205.tar.gz')

        row: Optional[Query] = select_from_doc ('2012.02205', 1)
        assert row is not None, 'Insert failed to write. Check test db configuration'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time is not None, \
            'Conversion end time not written'
        assert row.conversion_end_time > row.conversion_start_time, \
            f'End timestamp is not later than start: \
            {row.conversion_end_time} ≯ {row.conversion_start_time}'
        assert result, 'write_success should return True'
        
@pytest.mark.cc_unit_tests
def test_write_success_doc_overlap (app, insert_into_doc, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    assert os.path.exists('ancillary_files/3966840.tar.gz'), \
        'This test depends on tests/ancillary_files/3966840.tar.gz'
    with app.app_context():
        insert_into_doc (
            paper_id='2012.02205',
            document_version=3,
            conversion_status=0,
            latexml_version=app.config['LATEXML_COMMIT'],
            tex_checksum='5a67f1a2f9b1b436f2bd604e0131cf3a',
            conversion_start_time=now()
        )
        sleep(1)

        # Emulate old version being written while new is still processing
        old_version_result = write_success('2012.02205v3', 'ancillary_files/3966840.tar.gz')
        sleep(1)

        row: Optional[Query] = select_from_doc ('2012.02205', 3)
        assert row is not None, 'Insert failed to write. Check test db configuration'
        assert row.conversion_status == 0, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 0'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time is None, \
            f'Conversion end time was erroneously written: {row.conversion_end_time}'
        assert not old_version_result, 'write_success should return False'

        # Now new version finishes processing
        new_version_result = write_success('2012.02205v3', 'ancillary_files/2012.02205.tar.gz')

        row: Optional[Query] = select_from_doc ('2012.02205', 3)
        assert row is not None, 'Row is None'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time is not None, \
            'Conversion end time not written'
        assert row.conversion_end_time > row.conversion_start_time, \
            f'End timestamp is not later than start: \
            {row.conversion_end_time} ≯ {row.conversion_start_time}'
        assert new_version_result, 'write_success should return True'

@pytest.mark.cc_unit_tests
def test_write_success_doc_overlap_out_of_order (app, insert_into_doc, select_from_doc):
    assert os.path.exists('ancillary_files/2012.02205.tar.gz'), \
        'This test depends on tests/ancillary_files/2012.02205.tar.gz'
    assert os.path.exists('ancillary_files/3966840.tar.gz'), \
        'This test depends on tests/ancillary_files/3966840.tar.gz'
    with app.app_context():
        insert_into_doc (
            paper_id='2012.02205',
            document_version=3,
            conversion_status=0,
            latexml_version=app.config['LATEXML_COMMIT'],
            tex_checksum='5a67f1a2f9b1b436f2bd604e0131cf3a',
            conversion_start_time=now()
        )
        sleep(1)

        # Emulate new version beating the old version through the system
        new_version_result = write_success('2012.02205v3', 'ancillary_files/2012.02205.tar.gz')
        sleep(1)

        row: Optional[Query] = select_from_doc ('2012.02205', 3)
        end_time = row.conversion_end_time
        assert row is not None, 'Insert failed to write. Check test db configuration'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert end_time is not None, \
            'Conversion end time not written'
        assert end_time > row.conversion_start_time, \
            f'End timestamp is not later than start: \
            {end_time} ≯ {row.conversion_start_time}'
        assert new_version_result, 'write_success should return True'

        # Now new version finishes processing
        old_version_result = write_success('2012.02205v3', 'ancillary_files/3966840.tar.gz')

        row: Optional[Query] = select_from_doc ('2012.02205', 3)
        assert row is not None, 'Row is None'
        assert row.conversion_status == 1, \
            f'Incorrect conversion_status \'{row.conversion_status}\' should be 1'
        assert row.tex_checksum == '5a67f1a2f9b1b436f2bd604e0131cf3a', \
            f'Incorrect checksum: {row.tex_checksum}'
        assert row.conversion_end_time == end_time, \
            f'Conversion end time was rewritten. Expected {end_time} but \
            got {row.conversion_end_time}'
        assert not old_version_result, 'write_success should return False'

