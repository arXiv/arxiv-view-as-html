from typing import Any
import hashlib
import os

from models.db import DBLaTeXML
from models.util import transaction, now, current_session
from processing import get_file

from google.cloud.storage.blob import Blob


def _get_checksum (abs_fname: str) -> str:
    md5_hash = hashlib.md5()
    with open(abs_fname,"rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

def write_start (document_id: int, document_version: int, tar_fpath: str):
    with transaction() as session:
        rec = DBLaTeXML (
            document_id=document_id,
            document_version=document_version,
            conversion_status=0, # 0 for in progress, 1 for success, 2 for failure
            latexml_version=os.environ.get('LATEXML_COMMIT'),
            tex_checksum=_get_checksum(tar_fpath),
            conversion_start_time=now()
        )
        session.add(rec)

def write_success (document_id: int, document_version: int, tar_fpath: str) -> bool:
    success = False
    with transaction() as session:
        obj = session.query(DBLaTeXML) \
                .filter(DBLaTeXML.document_id == document_id) \
                .filter(DBLaTeXML.document_version == document_version) \
                .all()
        if len(obj) > 0:
            obj = obj[0]
            if obj.checksum == _get_checksum(tar_fpath) and \
                obj.latexml_version == os.environ.get('LATEXML_COMMIT') and \
                obj.conversion_status != 1:
                    obj.conversion_status = 1
                    obj.conversion_end_time = now()
                    success = True
    return success