from typing import List, Dict
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

def ddg_search(query: str, max_results: int = 5) -> List[Dict]:
    """بحث خفيف عبر DuckDuckGo (بدون مفاتيح)."""
    url = "https://duckduckgo.com/html/"
    params = {"q": query}
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.select("a.result__a")[:max_results]:
        title = a.get_text(" ", strip=True)
        href = a.get("href")
        results.append({"title": title, "url": href})
    return results

def fetch_page(url: str, max_len: int = 20000) -> str:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # إزالة العناصر غير المهمة
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return text[:max_len]
