import os
from pathlib import Path

from google.cloud.storage import Blob

from arxiv.files import FileObj, LocalFileObj
from arxiv.files.object_store import GsObjectStore

class WritableGSObjectStore (GsObjectStore):

    def write_obj (self, obj_in: FileObj, obj_out: Blob) -> None:
        if obj_out.exists():
            obj_out.delete()
        with obj_in.open('rb') as f_in:
            with obj_out.open('wb') as f_out:
                f_out.write(f_in.read())

    def copy_local_dir (self, path_in: str, path_out: str) -> None:
        for root, _, fnames in os.walk(path_in):
            for fname in fnames:
                abs_fpath = os.path.join(root, fname)
                obj_in = LocalFileObj(Path(abs_fpath))
                obj_out = self.bucket.blob(
                    os.path.join(
                        path_out,
                        os.path.relpath(
                            abs_fpath,
                            path_in
                        )
                    )
                )
                self.write_obj(obj_in, obj_out)