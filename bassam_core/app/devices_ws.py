# bassam_core/app/devices_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio
import json
from typing import Dict
import os

router = APIRouter()
# في الذاكرة: device_id -> websocket
CONNECTED_DEVICES: Dict[str, WebSocket] = {}

# بسيط: تحقق توكن (يمكن تحسين لاحقًا)
def valid_token(token: str) -> bool:
    allowed = os.getenv("DEVICE_SHARED_TOKEN", "").split(",")
    return token and token in allowed

@router.websocket("/ws/device")
async def device_ws_endpoint(websocket: WebSocket):
    # يتوقع رسالة تسجيل JSON: {"device_id":"id","token":"..."}
    await websocket.accept()
    try:
        auth = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        info = json.loads(auth)
        device_id = info.get("device_id")
        token = info.get("token")
        if not device_id or not valid_token(token):
            await websocket.send_text(json.dumps({"error":"auth_failed"}))
            await websocket.close()
            return
        CONNECTED_DEVICES[device_id] = websocket
        await websocket.send_text(json.dumps({"ok":"registered", "device_id": device_id}))
        # بقاء الاتصال واستقبال رسائل إن جاءت من الوكيل (logs أو heartbeats)
        while True:
            try:
                msg = await websocket.receive_text()
                # يمكن هنا حفظ مخرجات تنفيذ من الوكيل
                # رسالة متوقعة JSON: {"type":"result","cmd_id":"...","output":"...","status":"ok"}
                try:
                    obj = json.loads(msg)
                    # ببساطة اطبعها في لوج السيرفر
                    print("device->", device_id, obj)
                except Exception:
                    print("raw from device", device_id, msg)
            except WebSocketDisconnect:
                break
    except Exception as e:
        print("WS auth/recv error:", e)
    finally:
        try:
            CONNECTED_DEVICES.pop(device_id, None)
        except Exception:
            pass
