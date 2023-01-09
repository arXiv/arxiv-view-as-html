import tarfile
import os
import re
from google.cloud import storage
import subprocess

client = storage.Client()

def process (payload):
    # Outline
    try:
        tar = get_file(payload)
        source = untar(tar)
        main = find_main_tex_source(source)
        output = do_latexml(main, 'TODO') # need to get submissionId from somewhere; probably blob name
        upload_output(output)
    except:
        return False
    return True

def get_file(payload):
    blob = client.bucket(payload.payload['bucket']) \
        .blob(payload['name'])
    blob.download_to_filename('tar')
    return os.path.abspath('./tar')

def untar (fpath):
    with tarfile.open(fpath) as tar:
        tar.extractall('./source')
        tar.close()
    return os.path.abspath('./source')

def find_main_tex_source(path):
    # assuming path is a directory containing unzipped tex source etc
    tex_files = [f for f in os.listdir(path) if f.endswith('.tex')]
    if len(tex_files) == 1:
        return(os.path.join(path, tex_files[0]))
    else:
        main_files = {}
        for tf in tex_files:
            file = open(os.path.join(path, tf), "r")
            for line in file:
                if re.search(r"^\s*\\document(?:style|class)", line):
                    # https://arxiv.org/help/faq/mistakes#wrongtex
                    # according to this page, there should only be one tex file with a \documentclass - the main file ?
                    if tf == "paper.tex" or tf == "main.tex" or tf == "ms.tex" or tf == "article.tex":
                        main_files[tf] = 1
                    else:
                        main_files[tf] = 0
                    break
            file.close
        if len(main_files) == 1:
           return(os.path.join(path, list(main_files)[0]))
        else:
            # account for the two main ways of creating multi-file submissions on overleaf (standalone, subfiles)
            for mf in main_files:
                file = open(os.path.join(path, mf), "r")
                for line in file:
                    if re.search(r"^\s*\\document(?:style|class).*(?:\{standalone\}|\{subfiles\})", line):
                        main_files[mf] = -99999
                        break
                        # document class of main should not be standalone or subfiles (the main file is just {article} or something else)
                file.close
            return(os.path.join(path, max(main_files, key=main_files.get)))

def do_latexml (main_fpath, out_fpath):
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
        f"--source={main_fpath}", f"--dest={out_fpath}"] # TODO: will eventually need unique identifiers for the output files
    try:
        subprocess.run(config)
        return os.path.abspath('./main.html')
    except:
        return None

def upload_output (fpath, target):
    pass