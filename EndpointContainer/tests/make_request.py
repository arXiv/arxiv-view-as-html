import subprocess
from time import sleep
import requests


def get_signed_url (fname):
    url = "https://html-endpoint-6lhtms3oua-uc.a.run.app/upload"
    form = {'submission_id' : fname}
    req = requests.post(url, data=form)
    print (req.content)
    return req.json()['url']

def upload_to_signed_url (url, fname):
    command = ["curl", "-X", "PUT", "-H", "'Content-Type: application/octet-stream'", "--upload-file", fname, url]
    subprocess.run(command)

def download (fname):
    url = f"https://html-endpoint-6lhtms3oua-uc.a.run.app/download?submission_id={fname}"
    req = requests.get(url)
    return req.content

def do_whole_process (fname):
    signed_url = get_signed_url(fname)
    upload_to_signed_url(signed_url, fname)
    for i in range(90):
        print (f"Processing... {90 - i} seconds left")
        sleep(1)
    return download(fname)


if __name__ == '__main__':
    # Right now, this assumed that this file and the other file are in the same dir
    # Also assumes you run from that dir, because curl cares
    a = do_whole_process('2302.11573')
    # a = download('2302.11573')
    with open('temp1.html', 'wb') as f:
        f.write(a)
    print (a)
    # subprocess.run(['firefox', 'temp.html'])
    # import tarfile
    # with tarfile.open('2302.11573') as tar:
    #     #tar.extractall('./static')
    #     tar.extractall('./')
    #     tar.close()
