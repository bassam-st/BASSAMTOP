import os, json
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv
load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY")
RSA_PRIVATE_PATH = os.getenv("RSA_PRIVATE_PATH", "keys/rsa_private.pem")
RSA_PUBLIC_PATH  = os.getenv("RSA_PUBLIC_PATH",  "keys/rsa_public.pem")
def _get_fernet():
    global FERNET_KEY
    if not FERNET_KEY:
        try:
            with open("keys/fernet.key","rb") as f:
                FERNET_KEY = f.read().strip().decode()
        except:
            raise RuntimeError("FERNET_KEY not set. Run scripts/generate_keys.py and set FERNET_KEY.")
    key = FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY
    return Fernet(key)
def encrypt_json(obj: dict) -> str:
    f = _get_fernet()
    raw = json.dumps(obj, ensure_ascii=False).encode()
    token = f.encrypt(raw)
    return token.decode()
def decrypt_json(token: str) -> dict:
    f = _get_fernet()
    try:
        raw = f.decrypt(token.encode())
        return json.loads(raw.decode())
    except InvalidToken as e:
        raise RuntimeError("Invalid token or wrong key.") from e
