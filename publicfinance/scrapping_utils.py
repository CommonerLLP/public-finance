"""
Python 3 port of cbgaindia/scrapers/scrapping_utils.py
Original: https://github.com/cbgaindia/scrapers/blob/master/scrapping_utils.py
Changes: Python 2 -> 3 exception syntax, stealth headers added, logging simplified
"""

import logging
import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import shutil
from lxml import etree

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_XPATH = ".//text()"
TEXT_DOC_XPATH = "//text()"
MAX_RETRIES = 5

STEALTH_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class ScrappingUtils(object):
    def __init__(self, max_retries=MAX_RETRIES, request_timeout=30, file_timeout=60, verify_ssl=True):
        """Initializes session with retry logic and stealth headers."""
        self.request_timeout = request_timeout
        self.file_timeout = file_timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update(STEALTH_HEADERS)
        retry = Retry(total=max_retries, backoff_factor=1,
                      status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def fetch_page(self, url):
        """Fetches URL and returns its textual content."""
        import time
        try:
            response = self.session.get(
                url,
                stream=True,
                timeout=self.request_timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
            time.sleep(2) # Be nice to the server
            return response.text
        except Exception as e:
            logger.error(f"Unable to fetch {url}: {e}")
            return ''

    def check_and_create_file_path(self, file_path):
        """Creates directory path if it doesn't exist."""
        try:
            os.makedirs(os.path.dirname(os.path.realpath(file_path)), exist_ok=True)
        except Exception as e:
            logger.error(f"Unable to create path for {file_path}: {e}")

    def fetch_and_save_file(self, url, file_path):
        """Fetches URL and saves it as a file."""
        try:
            self.check_and_create_file_path(file_path)
            response = self.session.get(
                url,
                stream=True,
                timeout=self.file_timeout,
                verify=self.verify_ssl,
            )
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
                logger.info(f"Saved: {file_path}")
                return True
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
        except Exception as e:
            logger.error(f"Unable to save file from {url}: {e}")
        return False

    def get_page_dom(self, url):
        """Fetches page and returns lxml DOM tree."""
        page_text = self.fetch_page(url)
        if page_text:
            return etree.HTML(page_text)
        return None

    def get_links_from_dom(self, dom_tree, xpath):
        """Fetches links from DOM using XPath."""
        return dom_tree.xpath(xpath)

    def get_links_from_url(self, url, xpath):
        """Fetches links from URL using XPath."""
        dom_tree = self.get_page_dom(url)
        if dom_tree is not None:
            return self.get_links_from_dom(dom_tree, xpath)
        return []

    def get_text_from_element(self, element, remove_new_lines=True,
                               xpath=None, join_operator=None):
        """Retrieves text from an lxml element."""
        xpath = xpath or DEFAULT_XPATH
        join_operator = join_operator or ' '
        element_text = join_operator.join(element.xpath(xpath))
        if remove_new_lines:
            element_text = re.sub(r"\s{2,}|\r\n", " ", element_text).strip()
        else:
            element_text = re.sub(r" {2,}|\r\n", " ", element_text).strip()
        return element_text

    def save_file_as_txt(self, page_text, file_path, xpath=TEXT_DOC_XPATH):
        """Saves HTML page text as TXT file."""
        dom_tree = etree.HTML(page_text)
        doc_text = self.get_text_from_element(
            dom_tree, remove_new_lines=False, xpath=xpath, join_operator="\n"
        )
        doc_text = re.sub(r"\n{2,}", "\n", doc_text)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(doc_text)
