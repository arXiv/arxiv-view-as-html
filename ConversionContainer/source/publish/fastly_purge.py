import logging

from flask import current_app

def fastly_purge_abs (paper_id: str, version: int, fastly_key: str):
    headers = {
        "Fastly-Key": fastly_key,
        "Accept": "application/json",
    }
    domains = ["arxiv.org", "web3.arxiv.org", "www.arxiv.org"]
    
    for domain in domains:
        url = f"https://{ domain }/abs/{ paper_id }"

        response = requests.request("PURGE", url, headers=headers)

        if response.status_code == 200:
            logging.info(f'successfully purged { url }')
        else:
            logging.warning(f'failed to purge { url }')

        url = f"https://{ domain }/abs/{ paper_id }v{ version }"

        response = requests.request("PURGE", url, headers=headers)

        if response.status_code == 200:
            logging.info(f'successfully purged { url }')
        else:
            logging.warning(f'failed to purge { url }')