import tarfile

def untar (fpath: str, dir_name: str):
    with tarfile.open(fpath) as tar:
        tar.extractall(dir_name)
        tar.close()