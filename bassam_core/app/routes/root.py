from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def home():
    html = """
    <html lang="ar">
      <head>
        <meta charset="utf-8"/>
        <title>Bassam-Core Online ✅</title>
        <style>
          body {background:#0b0f19;color:#fff;font-family:Tahoma,Arial,sans-serif;text-align:center;margin-top:18%}
          .btn{display:inline-block;margin-top:20px;padding:10px 20px;background:#4e46dc;color:#fff;text-decoration:none;border-radius:10px}
          .btn:hover{background:#6b63ff}
        </style>
      </head>
      <body>
        <h1>✅ Bassam-Core Online</h1>
        <p>النواة تعمل بنجاح! جرّب الواجهة التفاعلية:</p>
        <a class="btn" href="/docs">فتح واجهة الذكاء</a>
      </body>
    </html>
    """
    return html
