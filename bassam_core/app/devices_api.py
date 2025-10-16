# bassam_core/app/devices_api.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os, json, time, uuid
from typing import Dict, Any
from .devices_ws import CONNECTED_DEVICES
from workers.core_worker import enqueue_dialog  # كي يمكن تسجيل الحوارات إن رغبت

router = APIRouter()

# مكان حفظ الأوامر المؤقتة
CMD_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "pending_commands.json")
os.makedirs(os.path.dirname(CMD_STORE), exist_ok=True)

def _load_cmds() -> Dict[str, Any]:
    try:
        with open(CMD_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cmds(d):
    with open(CMD_STORE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

class CmdRequest(BaseModel):
    device_id: str
    command: str
    description: str | None = None

@router.post("/device/command/request")
async def request_command(req: CmdRequest):
    """تنشئ طلب أمر؛ يظل في القائمة حتى توافق عليه صراحة"""
    # تحقق من وجود الجهاز المسجل
    device_ws = CONNECTED_DEVICES.get(req.device_id)
    cmd_id = str(uuid.uuid4())
    store = _load_cmds()
    store[cmd_id] = {
        "cmd_id": cmd_id,
        "device_id": req.device_id,
        "command": req.command,
        "description": req.description or "",
        "ts": int(time.time()),
        "status": "pending",   # pending, approved, sent, executed, failed, rejected
        "result": None
    }
    _save_cmds(store)
    return {"status":"queued", "cmd_id": cmd_id, "device_connected": bool(device_ws)}

@router.post("/device/command/approve/{cmd_id}")
async def approve_command(cmd_id: str):
    """أنت توافق على إرسال الأمر إلى الوكيل المُسجل."""
    store = _load_cmds()
    cmd = store.get(cmd_id)
    if not cmd:
        raise HTTPException(404, "cmd not found")
    if cmd["status"] != "pending":
        raise HTTPException(400, f"bad status {cmd['status']}")
    # تحقق أن الوكيل متصل
    ws = CONNECTED_DEVICES.get(cmd["device_id"])
    if not ws:
        cmd["status"] = "rejected"
        _save_cmds(store)
        raise HTTPException(400, "device not connected")
    # أعِد حالة ومحتوى وأرسل عبر WS
    payload = {
        "type": "execute",
        "cmd_id": cmd_id,
        "command": cmd["command"],
        "ts": int(time.time())
    }
    try:
        await ws.send_text(json.dumps(payload))
        cmd["status"] = "sent"
        cmd["sent_ts"] = int(time.time())
        _save_cmds(store)
        return {"status":"sent", "cmd_id": cmd_id}
    except Exception as e:
        cmd["status"] = "failed"
        cmd["result"] = str(e)
        _save_cmds(store)
        raise HTTPException(500, "send failed")

@router.post("/device/command/result/{cmd_id}")
async def command_result(cmd_id: str, payload: Dict[str, Any]):
    """استقبال نتيجة تنفيذ من الوكيل. (يُفعل من الوكيل عبر WS أو HTTP)"""
    store = _load_cmds()
    cmd = store.get(cmd_id)
    if not cmd:
        raise HTTPException(404, "cmd not found")
    cmd["status"] = payload.get("status", "executed")
    cmd["result"] = payload.get("output")
    cmd["exec_ts"] = int(time.time())
    _save_cmds(store)
    return {"ok": True}

@router.get("/devices")
async def list_devices():
    return {"connected": list(CONNECTED_DEVICES.keys())}

@router.get("/device/commands")
async def list_commands():
    return _load_cmds()
