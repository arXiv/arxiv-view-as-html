import requests
import subprocess
from time import sleep

def get_signed_url (fname):
    url = "https://endpoint-gp2ubwi5mq-uc.a.run.app/upload"
    form = {'submission_id' : fname}
    req = requests.post(url, data=form)
    print (req.content)
    return req.json()['url']

def upload_to_signed_url (url, fname):
    command = ["curl", "-X", "PUT", "-H", "'Content-Type: application/octet-stream'", "--upload-file", fname, url]
    subprocess.run(command)

def download (fname):
    url = "https://endpoint-gp2ubwi5mq-uc.a.run.app/download"
    form = {'submission_id' : fname}
    req = requests.post(url, data=form)
    return req.content

def do_whole_process (fname):
    signed_url = get_signed_url(fname)
    upload_to_signed_url(signed_url, fname)
    for i in range(120):
        print (f"Processing... {120 - i} seconds left")
        sleep(1)
    print (download(fname))


if __name__ == '__main__':
    # Right now, this assumed that this file and the other file are in the same dir
    # Also assumes you run from that dir, because curl cares
    # do_whole_process('2302.11573')
    a = download('2302.11573')
    print (a)
