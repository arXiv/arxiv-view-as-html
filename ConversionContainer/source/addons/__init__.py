from typing import Dict
from jinja2 import Template
from bs4 import BeautifulSoup
from ..exceptions import HTMLInjectionError
import os
import shutil

def _inject_html_addon (soup: BeautifulSoup, parent_tag: str, position: int, payload_fpath: str, **template_args: Dict[str, str]) -> BeautifulSoup:
    """
    Injects arbitrary html into the given parent tag in the src
    html file. The payload is placed inside the provided parent tag
    at the given position

    Parameters
    ----------
    src_fpath : String
        File path to the html files, relative to the
        /arxiv/conversion/addons/html/ dir, where all the html 
        should live
    payload_fpath : String
        The path to the html to be injected
    parent_tag: str
        The tag of the parent element. Usually 'head' or 'body'
    position : int
        The numerical index of the position of the element in the subtree of the parent_tag
    """
    try:
        with open(f'/arxiv/conversion/addons/html/{payload_fpath}', 'r') as payload:
            template = Template(payload.read())
            block = BeautifulSoup(template.render(**template_args), 'html.parser')
            soup.find(parent_tag).insert(position, block)
            return soup
    except Exception as exc:
        raise HTMLInjectionError(f"Failed to inject {payload_fpath} with {exc}") from exc
      

def inject_addons (src_fpath: str, identifier: str):
    
    with open(f'{src_fpath}', 'r+') as source:
        soup = BeautifulSoup(source.read(), 'html.parser')
        # Inject base tag into head
        # soup = _inject_html_addon(soup, 'head', 6, 'base.html', base_path=identifier.replace('.', '-'))
        # Inject header block into body
        soup = _inject_html_addon(soup, 'body', 1, 'header.html')
        # Inject body message into body
        soup = _inject_html_addon(soup, 'body', 2, 'body_message.html')
        # Inject style block into head
        soup = _inject_html_addon(soup, 'head', 7, 'style.html')

        # Add id="main" to <div class="ltx_page_main">
        soup.find('div', {'class': 'ltx_page_main'})['id'] = 'main'
        
        # Overwrite original file with the new addons
        source.seek(0)
        source.write(str(soup))
    
def copy_static_assets (src_fpath: str):
    shutil.copytree('/arxiv/source/addons/images', os.path.join(src_fpath, 'images'))