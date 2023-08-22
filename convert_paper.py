import argparse
import re
import requests

def print_error ():
    print ("""
            FAILURE... PLEASE MAKE SURE THE FOLLOWING ARE TRUE
                * paper is correctly formatted with version number (e.g. 2307.11045v1)
                * version is most current version """
           )

# arXiv ID format used from 2007-04 to present
RE_ARXIV_NEW_ID = re.compile(
    r'^(?P<yymm>(?P<yy>\d\d)(?P<mm>\d\d))\.(?P<num>\d{4,5})'
    r'(v(?P<version>[1-9]\d*))?([#\/].*)?$'
)

# arg parser
parser = argparse.ArgumentParser(
    description='Convert arxiv paper to html',
)

parser.add_argument('paper')

args = parser.parse_args()

if args.paper:

    if re.match(RE_ARXIV_NEW_ID, args.paper):
        archive = 'arxiv'
        id = args.paper
        orig = 'ftp'
        yymm = args.paper.split('.')[0]
        blob = f'{orig}/{archive}/papers/{yymm}/{args.paper}.tar.gz'

        response = requests.post('https://services.arxiv.org/latexml/single-convert', json={
            'id': args.paper,
            'blob': blob,
            'bucket': 'arxiv-production-data'
        })

        if response.status_code != 200:
            print_error()

    else:
        print_error()

else:
    print_error()