from typing import Optional
import re

def license_url_to_str_mapping (url: Optional[str]) -> str:
    if not url:
        return 'No License'
    elif url == 'http://arxiv.org/licenses/nonexclusive-distrib/1.0/':
        license = 'arXiv.org perpetual non-exclusive license'
    elif url == 'http://creativecommons.org/licenses/by-nc-nd/4.0/':
        license = 'CC BY-NC-ND 4.0'
    elif url == 'http://creativecommons.org/licenses/by-sa/4.0/':
        license = 'CC BY-SA 4.0'
    elif url == 'http://creativecommons.org/publicdomain/zero/1.0/' or url == 'http://creativecommons.org/licenses/publicdomain/':
        license = 'CC Zero'
    elif (match := re.match(r'http:\/\/creativecommons\.org\/licenses\/by-nc-sa\/(\d\.0)\/', url)):
        license = f'CC BY-NC-SA {match.group(1)}'
    elif (match := re.match(r'http:\/\/creativecommons\.org\/licenses\/by\/(\d\.0)\/', url)):
        license = f'CC BY {match.group(1)}'
    return f'License: {license}'
