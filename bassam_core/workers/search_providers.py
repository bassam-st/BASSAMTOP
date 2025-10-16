# bassam_core/workers/search_providers.py
import os
from typing import List, Dict
from duckduckgo_search import DDGS

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID", "").strip()

def search_ddg(q: str, max_results: int = 8) -> List[Dict]:
    out: List[Dict] = []
    with DDGS() as ddg:
        for r in ddg.text(q, max_results=max_results):
            out.append({
                "title": r.get("title"),
                "url": r.get("href") or r.get("url"),
                "summary": r.get("body") or r.get("snippet"),
                "source": "duckduckgo",
            })
    return out

def search_google(q: str, max_results: int = 8) -> List[Dict]:
    # يتطلب GOOGLE_API_KEY و GOOGLE_CSE_ID (Programmable Search)
    import json, urllib.parse, urllib.request
    if not (GOOGLE_API_KEY and GOOGLE_CSE_ID):
        return []
    params = urllib.parse.urlencode({
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": q,
        "num": max_results
    })
    url = f"https://www.googleapis.com/customsearch/v1?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = data.get("items", []) or []
    out: List[Dict] = []
    for it in items:
        out.append({
            "title": it.get("title"),
            "url": it.get("link"),
            "summary": (it.get("snippet") or "").strip(),
            "source": "google",
        })
    return out
