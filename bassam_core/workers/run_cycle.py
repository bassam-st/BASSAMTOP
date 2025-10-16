from typing import Optional, List, Dict
from bassam_core.search import ddg_search, fetch_page
from bassam_core.summarize import summarize_chunks
from bassam_core.storage import save_doc, save_summary, set_state, dequeue_query

DEFAULT_QUERY = "الذكاء الاصطناعي"

def _pipeline(query: str) -> Dict:
    results = ddg_search(query, max_results=5)
    pages: List[str] = []
    saved_items = []
    for r in results[:3]:
        try:
            txt = fetch_page(r["url"])
            pages.append(txt)
            doc_id = save_doc(r["url"], r["title"], txt)
            saved_items.append({"title": r["title"], "url": r["url"], "doc_id": doc_id})
        except Exception:
            continue
    summary = summarize_chunks(query, pages if pages else ["لم يتم جلب محتوى كافٍ."])
    sum_id = save_summary(query, saved_items, summary)
    return {"summary_id": sum_id, "query": query, "sources": saved_items}

def run_once(forced_query: Optional[str] = None) -> Dict:
    q = forced_query or dequeue_query() or DEFAULT_QUERY
    set_state(active=True, last_query=q)
    info = _pipeline(q)
    st = set_state(active=False, last_run=info["summary_id"], runs=get_state().get("runs",0)+1)  # type: ignore
    return {"ran": True, **info, "state": st}
