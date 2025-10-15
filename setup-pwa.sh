#!/usr/bin/env bash
set -e

ROOT="$PWD"
APPDIR="$ROOT/bassam-core"
STATIC="$APPDIR/static"
ICONDIR="$STATIC/icons"

mkdir -p "$STATIC" "$ICONDIR"

# 1) manifest.json
cat > "$STATIC/manifest.json" <<'MAN'
{
  "name": "Bassam AI Assistant",
  "short_name": "Bassam-AI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0b0f19",
  "theme_color": "#0b0f19",
  "scope": "/",
  "icons": [
    { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable" },
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ]
}
MAN

# 2) service-worker.js
cat > "$STATIC/service-worker.js" <<'SW'
const CACHE_NAME = "bassam-ai-cache-v1";
const OFFLINE_URLS = [
  "/",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k === CACHE_NAME ? null : caches.delete(k))))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  event.respondWith(
    caches.match(req).then((cached) => {
      return cached || fetch(req).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE_NAME).then((c) => c.put(req, copy));
        return resp;
      }).catch(() => cached);
    })
  );
});
SW

# 3) صفحة ترحيب بسيطة تحتوي روابط PWA (اختيارية – لأن لديك هوم HTML، لكن هذه نسخة فيها روابط PWA)
cat > "$STATIC/home.html" <<'HTML'
<!DOCTYPE html>
<html lang="ar">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Bassam-Core Online</title>
  <link rel="manifest" href="/static/manifest.json">
  <meta name="theme-color" content="#0b0f19"/>
  <style>
    body{background:#0b0f19;color:#fff;font-family:Tahoma,Arial,sans-serif;text-align:center;margin-top:10%}
    a.btn{display:inline-block;margin-top:22px;padding:10px 18px;background:#4e46dc;color:#fff;text-decoration:none;border-radius:10px}
    a.btn:hover{background:#6b63ff}
  </style>
</head>
<body>
  <h1>✅ Bassam-Core Online (PWA)</h1>
  <p>واجهة برمجية: <code>/api/chat</code></p>
  <p><a class="btn" href="/docs">فتح وثائق الـAPI</a></p>
  <script>
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/service-worker.js").catch(console.error);
    }
  </script>
</body>
</html>
HTML

# 4) إنشاء أيقونات PNG (192 و512) باستخدام Python Pillow
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
import os

icon_dir = os.path.join("bassam-core","static","icons")
os.makedirs(icon_dir, exist_ok=True)

def mk(size):
  img = Image.new("RGBA",(size,size),"#0b0f19")
  d = ImageDraw.Draw(img)
  # دائرة تدرّج بسيط
  d.ellipse((10,10,size-10,size-10), fill="#4e46dc")
  # كتابة BA
  txt = "BA"
  # محاولة اختيار خط افتراضي
  try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(size*0.42))
  except:
    font = ImageFont.load_default()
  w,h = d.textsize(txt,font=font)
  d.text(((size-w)/2,(size-h)/2), txt, font=font, fill="white")
  img.save(os.path.join(icon_dir,f"icon-{size}.png"))
for s in (192,512):
  mk(s)
print("Icons generated")
PY

# 5) تعديل app/main.py ليخدم static + manifest + SW ويعرض صفحة الـPWA
PYFILE="$APPDIR/app/main.py"
if ! grep -q "StaticFiles" "$PYFILE"; then
  # إدراج الاستيراد
  sed -i '1i from fastapi.staticfiles import StaticFiles' "$PYFILE"
fi

# إضافة mount للملفات الثابتة إذا غير موجود
if ! grep -q 'app.mount("/static"' "$PYFILE"; then
  echo 'app.mount("/static", StaticFiles(directory="bassam-core/static"), name="static")' >> "$PYFILE"
fi

# استبدال أو إضافة الهوم ليشير إلى صفحة الـPWA
python3 - <<'PY'
import io,sys,re
p = "bassam-core/app/main.py"
src = open(p,"r",encoding="utf-8").read()
# استبدال دالة home الحالية بـ صفحة static/home.html
pattern = r"@app\.get\(\"/\".*?def\s+home\([^)]*\):[\s\S]*?return .*"
new = """@app.get("/", response_class=HTMLResponse)
def home():
    with open("bassam-core/static/home.html", "r", encoding="utf-8") as f:
        return f.read()"""
src2 = re.sub(pattern, new, src, flags=re.M|re.S)
if src2==src:
    # لم يجد الدالة، نضيفها
    add = """
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    with open("bassam-core/static/home.html", "r", encoding="utf-8") as f:
        return f.read()
"""
    src2 = src + "\n" + add
open(p,"w",encoding="utf-8").write(src2)
print("main.py updated")
PY

# 6) إضافة Pillow للمتطلبات إذا غير موجود
REQ="$APPDIR/requirements.txt"
grep -q "^Pillow" "$REQ" || echo "Pillow" >> "$REQ"

echo "Installing/Updating dependencies..."
python3 -m pip install --no-user -r "$REQ" >/dev/null 2>&1 || true

echo "✅ PWA setup complete. Restart server to take effect."
echo "Run:  bash bassam-core/scripts/run_chat.sh"
