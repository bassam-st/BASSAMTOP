import requests
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse
import time
import urllib.robotparser

HEADERS = {"User-Agent": "BassamCoreBot/1.0 (+https://example.local)"}
RATE_SLEEP = 5  # وقت انتظار بين طلبات نفس الموقع (ثوان)

_cache_robots = {}

def allowed_by_robots(url):
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in _cache_robots:
            rp = _cache_robots[base]
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
            except:
                pass
            _cache_robots[base] = rp
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return False

def fetch_page_text(url, timeout=10):
    try:
        if not allowed_by_robots(url):
            return None
        time.sleep(RATE_SLEEP)
        r = requests.get(url, timeout=timeout, headers=HEADERS)
        r.raise_for_status()
        doc = Document(r.text)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(separator="\\n")
        return text
    except Exception:
        return None
