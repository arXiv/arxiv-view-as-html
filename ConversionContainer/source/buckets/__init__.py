import os
import tarfile

from .util import get_google_storage_client

def download_blob (bucket_name: str, blob_name: str, dst_fpath: str): 
    blob = get_google_storage_client() \
        .bucket(bucket_name).blob(blob_name)
    with open(dst_fpath, 'wb') as read_stream:
        blob.download_to_file(read_stream)
        read_stream.close()

def delete_blob (bucket_name: str, blob_name: str):
    get_google_storage_client() \
        .bucket(bucket_name).blob(blob_name).delete()

    
def upload_dir_to_gcs (src_dir: str, bucket_name: str):
    """
    Uploads the directory subtree of the given directory to the 
    given GCS bucket

    Parameters
    ----------
    src_dir : str
        path to the directory to be uploaded. This should be 
        in the form of ./extracted/{id}/html/ for conversion
    bucket_name : str
        name of bucket to upload to
    """
    bucket = get_google_storage_client().bucket(bucket_name)
    for root, _, fnames in os.walk(src_dir):
        for fname in fnames:
            abs_fpath = os.path.join(root, fname)
            bucket.blob(
                os.path.relpath(
                    abs_fpath,
                    src_dir
                )
            ) \
            .upload_from_filename(abs_fpath)

def upload_tar_to_gcs (sub_id: int, src_dir: str, bucket_name: str, destination_fname: str) -> None:
    """
    Uploads a .tar.gz object named {destination_fname}
    containing a folder called "html" located at {path}
    to the bucket named {bucket_name}. 

    Parameters
    ----------
    path : str
        Directory path in the form of /.../.../sub_id/html 
        for conversion
    destination_fname : str
        What to name the .tar.gz object, should be the
        submission id.
    """
    with tarfile.open(destination_fname, "w:gz") as tar:
        tar.add(f'{src_dir}/{sub_id}', arcname=str(sub_id))
    bucket = get_google_storage_client().bucket(bucket_name)
    blob = bucket.blob(f'{sub_id}.tar.gz')
    blob.upload_from_filename(destination_fname)

   
