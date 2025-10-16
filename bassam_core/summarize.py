import os
from typing import List
from textwrap import shorten

# اختياري: استخدام OpenAI لو توفر المفتاح
USE_OPENAI = bool(os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

def _openai_summarize(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "لخّص المحتوى بإيجاز مع نقاط مرقمة ومصادر عند توفرها."},
                  {"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()

def _simple_extract(texts: List[str], max_chars: int = 1200) -> str:
    joined = "\n\n".join(shorten(t.replace("\r", " ").replace("\n", " "), width=600, placeholder="...") for t in texts)
    return joined[:max_chars]

def summarize_chunks(query: str, chunks: List[str]) -> str:
    if USE_OPENAI:
        prompt = f"الموضوع: {query}\n\nلخّص النقاط الأهم بإيجاز (٥-٨ نقاط) ثم اختم بفقرة 'الخلاصة'."
        prompt += "\n\nالنصوص:\n" + "\n\n---\n\n".join(chunks[:5])
        try:
            return _openai_summarize(prompt)
        except Exception as e:
            return f"تلخيص بسيط (سقوط نموذج):\n{_simple_extract(chunks)}\n\n[خطأ النموذج: {e}]"
    else:
        return "تلخيص سريع (محلي):\n" + _simple_extract(chunks)
