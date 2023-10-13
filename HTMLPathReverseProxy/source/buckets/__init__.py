from .util import get_google_storage_client

def download_blob (bucket_name: str, blob_name: str, dst_fpath: str):
    blob = get_google_storage_client() \
        .bucket(bucket_name).blob(blob_name)
    with open(dst_fpath, 'wb') as read_stream:
        blob.download_to_file(read_stream)
        read_stream.close()