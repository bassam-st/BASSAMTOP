Bassam-Core (LIGHT + Scheduler)
تشغيل مؤقت (Replit):
  1) قم بتعيين FERNET_KEY في Secrets بعد توليده.
  2) source venv/bin/activate
  3) uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir .
المجدول يقوم بجولات بحث كل 15 دقيقة. الجولة الأولى تعمل فور البدء.
