from typing import Dict
from jinja2 import Template
from bs4 import BeautifulSoup
from ..exceptions import HTMLInjectionError
import os
import shutil

ABS_URL_BASE = 'https://arxiv.org/abs'

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
        with open(f'/arxiv/source/addons/html/{payload_fpath}', 'r') as payload:
            template = Template(payload.read())
            block = BeautifulSoup(template.render(**template_args), 'html.parser')
            soup.find(parent_tag).insert(position, block)
            return soup
    except Exception as exc:
        raise HTMLInjectionError(f"Failed to inject {payload_fpath} with {exc}") from exc
    
def _strip_footer (soup: BeautifulSoup) -> BeautifulSoup:
    soup.find('footer').decompose()
    return soup

def _fix_nav (soup: BeautifulSoup) -> BeautifulSoup:
    soup.find('nav', {'class': 'ltx_page_navbar'}).replaceWithChildren() # delete outer nav
    nav = soup.find('nav', {'class': 'ltx_TOC'})
    nav['aria-labelledby'] = 'toc_header'
    nav.insert(0, BeautifulSoup('<h2 id="toc_header">Table of Contents</h2>', 'html.parser'))

    main = soup.find('div', {'id': 'main'})
    main.insert(0, nav)
    
    return soup

def post_process (src_fpath: str, identifier: str, is_submission: bool):

    with open(f'{src_fpath}', 'r+') as source:
        soup = BeautifulSoup(source.read(), 'html.parser')
        
        soup = _strip_footer(soup)

        soup = _fix_nav(soup)

        # Add id="main" to <div class="ltx_page_main">
        soup.find('div', {'class': 'ltx_page_main'})['id'] = 'main'
        
        # Overwrite original file with the new addons
        source.truncate(0)
        source.seek(0)
        source.write(str(soup))

