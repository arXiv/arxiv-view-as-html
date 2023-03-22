import tarfile
import os
import re
import config
import db
from google.cloud import storage
import subprocess
import shutil

# Change such that we can handle multiple requests
# Raise max requests allowed on cloud run
# Error handling try/catch - send event maybe

client = storage.Client()

def process (payload):
    try:
        submission_id = payload['name']
        if submission_id:
            db.write_in_progress(submission_id)
        else:
            raise Exception('No submission_id')
        print ("Step 1: downloading")
        tar = get_file(payload)
        print (f"Step 2: untarring {tar}")
        source = untar(tar, payload['name'])
        print ("Step 3: Removing .ltxml files")
        remove_ltxml (source)
        print ("Step 4: finding main tex source")
        main = find_main_tex_source(source)
        print (f"Main tex source is {main}")
        out_path = os.path.join(source, 'html')
        try:
            os.mkdir(out_path)
        except FileExistsError:
            for filename in os.listdir(out_path):
                filepath = os.path.join(out_path, filename)
                try:
                    shutil.rmtree(filepath)
                except OSError:
                    os.remove(filepath)
        print (f"Out path is {out_path}")
        print ("Step 5: Do LaTeXML")
        do_latexml(main, os.path.join(out_path, submission_id))
        print (f"Step 6: Upload html from {out_path}")
        upload_output(out_path, config.OUT_BUCKET_NAME, submission_id)
        print ("Uploaded successfully. Done!")
        db.write_success(submission_id)
    except:
        if payload.get('name'):
            db.write_failure(payload['name'])
        else:
            pass
            # what to do if we got a bad submission_id?
    finally:
        try:
            os.rmdir(payload['name'])
        except:
            print (f"Failed to delete {payload.get('name')}")
    return True

def get_file(payload):
    if payload['name'].endswith('.gz'):
        fname = payload['name'].split['/'][1].split['.'][0]
    else:
        raise Exception ("Not a tar")

    blob = client.bucket(payload['bucket']) \
        .blob(payload['name'])
    with open(fname, 'wb') as read_stream:
        blob.download_to_file(read_stream) # payload['name']
        read_stream.close()
    return os.path.abspath(f"./{fname}")

def remove_ltxml (path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if str(file).endswith('.ltxml'):
                 os.remove(os.path.join(root, file))

def untar (fpath, dir_name):
    # WE MAKE AN ASSUMPTION THAT WE ARE RECEIVING A tar gz file, with no file extension
    with tarfile.open(fpath) as tar:
        tar.extractall(f"extracted/{dir_name}") # Assuming they protect us from files with ../ or / in the name
        tar.close()
    return os.path.abspath(f"extracted/{dir_name}")

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
    config = ["latexmlc", \
        "--preload=[nobibtex,ids,localrawstyles,mathlexemes,magnify=2,zoomout=2,tokenlimit=99999999,iflimit=1499999,absorblimit=1299999,pushbacklimit=599999]latexml.sty", \
        "--path=/opt/arxmliv-bindings/bindings", \
        "--path=/opt/arxmliv-bindings/supported_originals", \
        "--pmml","--cmml","--mathtex", \
        "--timeout=2700", \
        "--nodefaultresources", \
        "--css=css/ar5iv.min.css", \
        f"--source={main_fpath}", f"--dest={out_fpath}.html"]
    subprocess.run(config)

def upload_output (path, bucket_name, destination_fname):
    try:
        with tarfile.open(destination_fname, "w:gz") as tar:
            tar.add(path, arcname=os.path.basename(path))
        with open(destination_fname, 'r') as temp:
            temp.seek(0, os.SEEK_END)
            print (f"Tar size: {temp.tell()}")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_fname)
        print (f"Blob info: {blob.name}")
        blob.upload_from_filename(destination_fname)
    finally:
        try:
            os.remove(destination_fname)
        except:
            print (f"Failed to delete {destination_fname}")
    
    