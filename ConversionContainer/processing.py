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
    """
    Runs latexml on the blob in the payload and uploads
    the results to the output bucket in the config
    file.

    Parameters
    ----------
    payload : JSON
        https://github.com/googleapis/google-cloudevents/blob/main/proto/google/events/cloud/storage/v1/data.proto

    Returns
    -------
    Boolean
        Returns true unless an exception occurs

    Raises
    ------
    Exception
        'No submission_id': No submission id (payload.name)
            contained in the payload. Likely the entire
            payload is invalid/malformed.
    """
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
    """
    Checks if the payload contains a .tar.gz file
    and if so it downloads the file to "fpath".
    Otherwise, it throws an Exception, ending the process
    and logging the non .tar.gz file.

    Parameters
    ----------
    payload : JSON
        https://github.com/googleapis/google-cloudevents/blob/main/proto/google/events/cloud/storage/v1/data.proto
    
    Returns
    -------
    fpath : String
        File path to the .tar.gz object
    """
    try:
        if payload['name'].endswith('.gz'):
            fname = payload['name'].split['/'][1].split['.'][0]
        else:
            raise Exception ("Not a tar")
    except Exception as e:
        print(f"{payload['name']} was not a .tar.gz")

    try:
        blob = client.bucket(payload['bucket']) \
            .blob(payload['name'])
        with open(fname, 'wb') as read_stream:
            blob.download_to_file(read_stream)
            read_stream.close()
        return os.path.abspath(f"./{fname}")
    except Exception as e:
        print(e)
        print(f"Downloading {payload['name']} failed")


def remove_ltxml (path):
    """
    Remove files with the .ltxml extension from the
    directory "path".

    Parameters
    ----------
    path : String
        File path to the directory containing unzipped .tex source
    """
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                if str(file).endswith('.ltxml'):
                    os.remove(os.path.join(root, file))
    except Exception as e:
        print(e)
        print(f"Removing .ltxml files from {path} failed")

def untar (fpath, dir_name):
    """
    Extracts the .tar.gz at "fpath" into directory
    "dir_name".

    Parameters
    ----------
    fpath : String
        File path to the .tar.gz object
    dir_name : String
        Name that we want to give to the directory
        that contains the extracted files

    Returns
    -------
    extracted_directory : String
        File path of the directory that contains the
        extracted files
    """
    try:
        with tarfile.open(fpath) as tar:
            tar.extractall(f"extracted/{dir_name}") # Assuming they protect us from files with ../ or / in the name
            tar.close()
        return os.path.abspath(f"extracted/{dir_name}")
    except Exception as e:
        print(e)
        print(f"Untarring {fpath} failed")

def find_main_tex_source(path):
    """
    Looks inside the directory at "path" and determines the
    main .tex source. Assumes that the main .tex file
    must start with "\documentclass". To account for
    common Overleaf templates that have multiple .tex
    files that start with "\documentclass", assumes that
    the main .tex file is not of class "standalone"
    or "subfiles".

    Parameters
    ----------
    path : String
        File path to a directory containing unzipped .tex source

    Returns
    -------
    main_tex_source : String
        File path to the main .tex source in the directory
    """
    try:
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
    except Exception as e:
        print(e)
        print(f"Finding main .tex source of {path} failed")


def do_latexml (main_fpath, out_fpath):
    """
    Runs latexml on the .tex file at main_fpath and
    outputs the html at out_fpath.

    Parameters
    ----------
    main_fpath : String
        Main .tex file path
    out_fpath : String
        Output directory file path
    """
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
    """
    Uploads a .tar.gz object named {destination_fname}
    containing a folder called "html" located at {path}
    to the bucket named {bucket_name}. 

    Parameters
    ----------
    path : String
        Directory path in format .../.../sub_id/html
        containing the static files for article html.
    bucket_name : String
        The name of the bucket to upload the object to.
    destination_fname : String
        What to name the .tar.gz object, should be the
        submission id.
    """
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
    except Exception as e:
        print(e)
        print("Uploading output failed")
    finally:
        try:
            os.remove(destination_fname)
        except:
            print (f"Failed to delete {destination_fname} in upload_output()")
    
    