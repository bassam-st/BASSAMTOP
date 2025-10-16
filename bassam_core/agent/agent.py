# bassam_core/agent/agent.py
# وكيل تنفيذ الأوامر الآمن لبسام الذكي

import os, asyncio, json, subprocess, sys, time
import websockets
from cryptography.fernet import Fernet

# 🧩 إعدادات من البيئة (Environment Variables)
SERVER_WS = os.getenv("SERVER_WS", "wss://your-render-domain.onrender.com/ws/device")
DEVICE_ID = os.getenv("DEVICE_ID", "device1")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "device-token-here")
FERNET_KEY = os.getenv("FERNET_KEY", "")  # نفس المفتاح المستخدم في الخادم

# ⚙️ تهيئة Fernet للتشفير (اختياري حاليًا)
def _get_fernet():
    if not FERNET_KEY:
        return None
    try:
        return Fernet(FERNET_KEY)
    except Exception as e:
        print("⚠️ Fernet key error:", e)
        return None

# 🚀 تنفيذ الأوامر داخل النظام المحلي
async def run_command(cmd: str, timeout: int = 30):
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            text = out.decode(errors="replace")
            return {"status": "ok", "output": text}
        except asyncio.TimeoutError:
            proc.kill()
            return {"status": "timeout", "output": "Execution timeout"}
    except Exception as e:
        return {"status": "error", "output": str(e)}

# 💡 حلقة التشغيل الرئيسية
async def agent_loop():
    print(f"🔗 Connecting to {SERVER_WS} as {DEVICE_ID}...")
    try:
        async with websockets.connect(SERVER_WS) as ws:
            # إرسال بيانات التسجيل
            await ws.send(json.dumps({"device_id": DEVICE_ID, "token": DEVICE_TOKEN}))
            reg_reply = await ws.recv()
            print("✅ Registration reply:", reg_reply)

            while True:
                msg = await ws.recv()
                try:
                    obj = json.loads(msg)
                except Exception:
                    print("⚠️ Received invalid message:", msg)
                    continue

                if obj.get("type") == "execute":
                    cmd_id = obj.get("cmd_id")
                    command = obj.get("command")
                    print(f"🧭 Executing command from server: {command}")
                    result = await run_command(command, timeout=60)

                    # إرسال النتيجة للخادم
                    payload = {
                        "type": "result",
                        "cmd_id": cmd_id,
                        "status": result["status"],
                        "output": result["output"][:2000],  # تقليم المخرجات الطويلة
                    }
                    await ws.send(json.dumps(payload))
    except Exception as e:
        print("❌ Connection error:", e)
        print("🔁 Retrying in 15s...")
        await asyncio.sleep(15)
        await agent_loop()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(agent_loop())
    except KeyboardInterrupt:
        print("🛑 Agent stopped manually.")
