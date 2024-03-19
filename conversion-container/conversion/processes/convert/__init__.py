"""Module that handles the conversion process from LaTeX to HTML"""
import os
import re
import shutil
from typing import (
    Any,
    List,
    Dict,
    Optional
)
import logging
import uuid
from bs4 import BeautifulSoup

from flask import current_app

from ...locking import id_lock
from ...buckets import (
    download_blob,
    upload_dir_to_gcs,
    upload_tar_to_gcs
)
from ...exceptions import *
# from ...concurrency_control import (
#     write_start,
#     write_success,
#     write_failure
# )
from ...domain.conversion import ConversionPayload
from ...services.files import get_file_manager
from ...services.latexml import latexml
from .metadata import generate_metadata

logger = logging.getLogger()

def process(conversion_payload: ConversionPayload) -> bool:
    # is_submission = bucket == current_app.config['IN_BUCKET_SUB_ID']

    # """ File system we will be using """
    # safe_name = str(uuid.uuid4()) # In case two machines download before locking
    # download_file = f'{safe_name}.gz' if single_file else f'{safe_name}.tar.gz' # the file we download the blob to
    # src_dir = f'extracted/{id}' # the directory we untar the blob to
    # bucket_dir_container = f'{src_dir}/html' # the directory we will upload the *contents* of
    # outer_bucket_dir = f'{bucket_dir_container}/{id}' # the highest level directory that will appear in the out bucket

    try:
        with id_lock(conversion_payload.name, current_app.config['LOCK_DIR']):
            logging.info(f"STARTING FOR {conversion_payload.name}")
            main_src = get_file_manager().download_source(conversion_payload)
            logging.info(f"MAIN SRC IS {str(main_src)}")

            # Write to DB that process has started
            # logger.info(f"{id}: Write start process to db")
            # write_start(id, download_file, is_submission)


            # remove_ltxml(src_dir) # TODO

            latexml_output = latexml(main_src, conversion_payload) # Also need to upload stdout

            metadata = generate_metadata(latexml_output.missing_packages, conversion_payload)

            get_file_manager().upload_latexml(conversion_payload, metadata)

            # TODO: Maybe remove for batch
            # download_blob(bucket, blob, download_file) # download again to double check for most recent tex source
            # write_success(id, download_file, is_submission)
    except Exception as e:
        logger.info(f'{conversion_payload.name}: Conversion unsuccessful', exc_info=1)
        logger.warn(e)
        # try:
        #     download_blob(bucket, blob, download_file)
        #     write_failure(id, download_file, is_submission)
        # except Exception as e:
        #     logger.warning(f'{id}: Failed to write failure', exc_info=1)
    # finally:
    #     try:
    #         with id_lock(id, current_app.config['LOCK_DIR'], 1):
    #             _clean_up(download_file, id)
    #     except Exception as e:
    #         logger.warning(f"{id}: Failed to clean up lock and dir", exc_info=1)


def remove_ltxml(path: str) -> None:
    """
    Remove files with the .ltxml extension from the
    directory "path".

    Parameters
    ----------
    path : str
        File path to the directory containing unzipped .tex source
    """
    try:
        for root, _, files in os.walk(path):
            for file in files:
                if str(file).endswith('.ltxml'):
                    os.remove(os.path.join(root, file))
    except Exception as exc:
        raise LaTeXMLRemoveError(
            f".ltxml file at {path} failed to be removed") from exc



# def insert_base_tag (fpath: str, id: str) -> None:
#     """ This inserts the base tag into the html so we can use the /html/arxiv_id url """
#     base_html = f'<base href="/html/{id}/">'

#     with open(fpath, 'r+') as html:
#         soup = BeautifulSoup(html.read(), 'html.parser')
#         soup.head.append(BeautifulSoup(base_html, 'html.parser'))
#         html.truncate(0)
#         html.seek(0)
#         html.write(str(soup))

# def replace_absolute_anchors_for_doc (fpath: str, id: str) -> None:
#     HREF_RE = re.compile(r'\/html\/submission\/\d+\/view#.+')
#     VIEW_DOC_BASE = current_app.config['VIEW_DOC_BASE']
#     with open(fpath, 'r+') as html:
#         soup = BeautifulSoup(html.read(), 'html.parser')
#         for a in soup.find_all('a', attrs={'class': 'ltx_ref'}):
#             if a.get('href') and re.search(HREF_RE, a['href']) is not None:
#                 relative_anchor = a['href'].split('/view')[1]
#                 a['href'] = f'{VIEW_DOC_BASE}/html/{id}{relative_anchor}'
#             elif a.get('href') and a['href'][0] == '#':
#                 a['href'] = f'{VIEW_DOC_BASE}/html/{id}{a["href"]}'
#             html.truncate(0)
#             html.seek(0)
#             html.write(str(soup))

# def insert_absolute_anchors_for_submission (fpath: str, sub_id: int) -> None:
#     VIEW_SUB_BASE = current_app.config['VIEW_SUB_BASE']
#     with open(fpath, 'r+') as html:
#         soup = BeautifulSoup(html.read(), 'html.parser')
#         for a in soup.find_all('a', attrs={'class': 'ltx_ref'}):
#             if a.get('href') and a['href'][0] == '#':
#                 a['href'] = f'{VIEW_SUB_BASE}/html/submission/{sub_id}/view{a["href"]}'
#         html.truncate(0)
#         html.seek(0)
#         html.write(str(soup))

# def insert_missing_package_warning (fpath: str, missing_packages: List[str]) -> None:
#     """ This is the HTML for the closeable pop up warning for missing packages """
#     missing_packages_lis = "\n".join(map(lambda x: f"<li>failed: {x}</li>", missing_packages))
#     popup_html = f"""
#         <div class="package-alerts ltx_document" role="status" aria-label="Conversion errors have been found">
#             <button aria-label="Dismiss alert" onclick="closePopup()">
#                 <span aria-hidden="true"><svg role="presentation" width="20" height="20" viewBox="0 0 44 44" aria-hidden="true" focusable="false">
#                 <path d="M0.549989 4.44999L4.44999 0.549988L43.45 39.55L39.55 43.45L0.549989 4.44999Z" />
#                 <path d="M39.55 0.549988L43.45 4.44999L4.44999 43.45L0.549988 39.55L39.55 0.549988Z" />
#                 </svg></span>
#             </button>
#             <p>HTML conversions <a href="https://info.dev.arxiv.org/about/accessibility_html_error_messages.html" target="_blank">sometimes display errors</a> due to content that did not convert correctly from the source. This paper uses the following packages that are not yet supported by the HTML conversion tool. Feedback on these issues are not necessary; they are known and are being worked on.</p>
#                 <ul arial-label="Unsupported packages used in this paper">
#                     {missing_packages_lis}
#                 </ul>
#             <p>Authors: achieve the best HTML results from your LaTeX submissions by following these <a href="https://info.arxiv.org/help/submit_latex_best_practices.html" target="_blank">best practices</a>.</p>
#         </div>

#         <script>
#             function closePopup() {{
#                 document.querySelector('.package-alerts').style.display = 'none';
#             }}
#         </script>
#         """
#     with open(fpath, 'r+') as html:
#         soup = BeautifulSoup(html.read(), 'html.parser')
#         soup.find('div', attrs={'class': 'ltx_page_content'}).insert(0, BeautifulSoup(popup_html, 'html.parser'))
#         html.truncate(0)
#         html.seek(0)
#         html.write(str(soup))

# def insert_license (fpath: str, id: str, is_submission: bool, is_missing_packages: Optional[List]):
#     if not is_submission:
#         paper_id, version = id.split('v')
#         license = get_license_for_paper(paper_id, int(version))
#     else:
#         license = get_license_for_submission(int(id))
#     license_html = BeautifulSoup(f'<div id="license-tr">{license}</div>', 'html.parser')
#     with open(fpath, 'r+') as html:
#         soup = BeautifulSoup(html.read(), 'html.parser')
#         target_section = soup.new_tag('div', attrs={'class': 'section', 'id': 'target-section'})
#         document_wrapper = soup.find('div', attrs={'class': 'ltx_page_content'})
#         if is_missing_packages:
#             document_wrapper \
#                 .find('div', attrs={'class': ['package-alerts', 'ltx_document']}) \
#                 .insert_after(target_section)
#         else:
#             document_wrapper.insert(0, target_section)
#         target_section.append(license_html)
#         html.truncate(0)
#         html.seek(0)
#         html.write(str(soup))

def _clean_up (tar, id):
    os.remove(tar)
    shutil.rmtree(f'extracted/{id}')
