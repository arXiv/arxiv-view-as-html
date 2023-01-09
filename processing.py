import tarfile
import os
from google.cloud import storage
import subprocess

def process (payload):
    # Outline
    try:
        tar = get_file(payload)
        source = untar(tar)
        main = find_main_tex_source(source)
        output = do_latexml(main)
        upload_output(output)
    except:
        return False
    return True

def get_file(payload):
    client = storage.Client()
    blob = client.bucket(payload.payload['bucket']) \
        .blob(payload['name'])
    blob.download_to_filename('tar')
    return os.path.abspath('./tar')

def untar (fpath):
    with tarfile.open(fpath) as tar:
        tar.extractall('./source')
        tar.close()
    return os.path.abspath('./source')

def find_main_tex_source (path):
    pass # TODO

def do_latexml (main_fpath):
    # TODO: the executable might be in a different place
    # TODO: will probably want keep the css in the container
    #       to really limit incoming requests
    config = ["/opt/latexml/bin/latexmlc", \
        "--preload=[nobibtex,ids,localrawstyles,mathlexemes,magnify=2,zoomout=2,tokenlimit=99999999,iflimit=1499999,absorblimit=1299999,pushbacklimit=599999]latexml.sty", \
        "--path=/opt/arxmliv-bindings/bindings", \
        "--path=/opt/arxmliv-bindings/supported_originals", \
        "--pmml","--cmml","--mathtex", \
        "--timeout=2700", \
        "--nodefaultresources", \
        "--css=https://cdn.jsdelivr.net/gh/dginev/ar5iv-css@0.7.4/css/ar5iv.min.css", \
        f"--source={main_fpath}", "--dest=main.html"] # TODO: will eventually need unique identifiers for the output files
    try:
        subprocess.run(config)
        return os.path.abspath('./main.html')
    except:
        return None

def upload_output (fpath, target):
    pass # TODO
    
    