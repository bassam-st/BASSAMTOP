import os, json, time, re, asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

import httpx
import feedparser
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

KNOW_PATH = os.path.join(DATA_DIR, "knowledge.jsonl")   # تخزين التعلم التراكمي
STATE_PATH = os.path.join(DATA_DIR, "learn_state.json") # حالة آخر تشغيل

DEFAULT_INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "30"))

# مصادر RSS موثوقة (تقدر تزيد/تقلل)
RSS_SOURCES = [
    "https://hnrss.org/frontpage",                 # Hacker News
    "https://aws.amazon.com/blogs/aws/feed/",      # AWS
    "https://cloud.google.com/blog/topics/developers-practitioners.xml",
    "https://engineering.atspotify.com/feed/",
    "https://netflixtechblog.com/feed",
    "https://slack.engineering/feed/",
    "https://martinfowler.com/feed.atom",
    "https://kubernetes.io/feed.xml",
]

# نطاقات مقيَّدة للبحث site:
SITE_WHITELIST = [
    "developer.apple.com", "developer.android.com", "cloud.google.com",
    "docs.aws.amazon.com", "learn.microsoft.com", "kubernetes.io",
    "pytorch.org", "tensorflow.org", "python.org", "fastapi.tiangolo.com",
    "www.cloudflare.com", "nginx.org", "microsoft.github.io",
]

SEARCH_QUERIES = [
    "build ai assistant fastapi best practices",
    "python secure command execution sandbox",
    "websocket python examples production",
    "mobile device diagnostics adb fastboot guide",
    "network troubleshooting cli cheatsheet",
    "linux hardening tips sysadmin",
    "android system repair flashing basics",
    "secure crypto fernet how to rotate keys",
]

def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # حذف سكربت وستايل
    for tag in soup(["script", "style", "noscript"]): tag.decompose()
    text = soup.get_text(" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _summarize(text: str, max_chars: int = 600) -> str:
    # ملخص بسيط: أول فقرات/جمل حتى حد
    return (text[:max_chars] + "…") if len(text) > max_chars else text

async def _fetch(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception:
        return ""

def _write_jsonl(path: str, doc: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False) + "\n")

def _save_state(state: Dict[str, Any]) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def _load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH): return {}
    try:
        return json.load(open(STATE_PATH, "r", encoding="utf-8"))
    except Exception:
        return {}

async def gather_from_rss(limit_per_feed: int = 5) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for feed in RSS_SOURCES:
            d = feedparser.parse(feed)
            for e in d.entries[:limit_per_feed]:
                url = e.get("link")
                if not url: continue
                html = await _fetch(client, url)
                if not html: continue
                text = _clean_text(html)
                if not text: continue
                items.append({
                    "source": "rss",
                    "feed": feed,
                    "url": url,
                    "title": e.get("title", ""),
                    "summary": _summarize(text),
                    "ts": datetime.now(timezone.utc).isoformat()
                })
    return items

async def gather_from_search(max_per_query: int = 5) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    site_filter = " OR ".join([f"site:{s}" for s in SITE_WHITELIST])
    async with httpx.AsyncClient(follow_redirects=True) as client, DDGS() as ddgs:
        for q in SEARCH_QUERIES:
            query = f"{q} ({site_filter})"
            for r in ddgs.text(query, max_results=max_per_query, region="wt-wt"):
                url = r.get("href") or r.get("url")
                title = r.get("title") or ""
                if not url: continue
                html = await _fetch(client, url)
                if not html: continue
                text = _clean_text(html)
                if not text: continue
                items.append({
                    "source": "search",
                    "query": q,
                    "url": url,
                    "title": title,
                    "summary": _summarize(text),
                    "ts": datetime.now(timezone.utc).isoformat()
                })
    return items

async def auto_learn_once() -> Dict[str, Any]:
    start = time.time()
    rss_docs = await gather_from_rss()
    search_docs = await gather_from_search()

    new_docs = rss_docs + search_docs
    for doc in new_docs:
        _write_jsonl(KNOW_PATH, doc)

    state = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "added": len(new_docs),
        "duration_sec": round(time.time() - start, 2)
    }
    _save_state(state)
    return state

# جدولة داخلية (اختيارية لمناداة مباشرة)
async def schedule_auto_learn(interval_min: int = DEFAULT_INTERVAL_MIN):
    while True:
        try:
            await auto_learn_once()
        except Exception as e:
            _save_state({"error": str(e), "ts": datetime.now(timezone.utc).isoformat()})
        await asyncio.sleep(max(2, interval_min) * 60)

def get_learn_state() -> Dict[str, Any]:
    state = _load_state()
    state.setdefault("interval_min", DEFAULT_INTERVAL_MIN)
    return state

def get_latest_knowledge(limit: int = 20) -> List[Dict[str, Any]]:
    if not os.path.exists(KNOW_PATH): return []
    lines = open(KNOW_PATH, "r", encoding="utf-8").read().splitlines()
    docs = [json.loads(x) for x in lines[-limit:]]
    return list(reversed(docs))
