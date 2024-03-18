from typing import Optional
import re
from bs4 import BeautifulSoup

from google.cloud import storage
import google.cloud.logging

def get_google_storage_client ():
    return storage.Client()
