import logging
import os
import re
import requests
from requests.adapters import HTTPAdapter
import shutil
from lxml import etree

# Modernized version of CBGA ScrappingUtils for Python 3
class OBIUtils(object):
    def __init__(self):
        self.session = requests.Session()
        # Add stealth headers to bypass simple bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.session.mount('http://', HTTPAdapter(max_retries=5))
        self.session.mount('https://', HTTPAdapter(max_retries=5))

    def fetch_page(self, url):
        try:
            response = self.session.get(url, timeout=20)
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ''

    def get_page_dom(self, url):
        page_text = self.fetch_page(url)
        if page_text:
            return etree.HTML(page_text)
        return None

    def fetch_and_save_file(self, url, file_path):
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            response = self.session.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                return True
        except Exception as e:
            print(f"Error saving file from {url}: {e}")
        return False
