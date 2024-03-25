# from typing import Optional
# from bs4 import BeautifulSoup
# from .db_queries import get_submission_timestamp, get_version_primary_category

# def make_published_watermark (submission_id: int, paper_id: str, version: int) -> Optional[BeautifulSoup]:
#     timestamp = get_submission_timestamp(submission_id)
#     category = get_version_primary_category(paper_id, version)
#     return BeautifulSoup(f'<div id="watermark-tr">arXiv:{paper_id}v{version} [{category}] {timestamp}</div>', 'html.parser')

# def insert_watermark (html_fpath: str, watermark: BeautifulSoup):
#     with open(html_fpath, 'r+') as html:
#         soup = BeautifulSoup(html.read(), 'html.parser')
#         soup.find('div', attrs={'id': 'target-section'}).append(watermark)
#         html.truncate(0)
#         html.seek(0)
#         html.write(str(soup))