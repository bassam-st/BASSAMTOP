import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

OUT_DIR = "keys"
os.makedirs(OUT_DIR, exist_ok=True)

def gen_fernet_key():
    key = Fernet.generate_key()
    path = os.path.join(OUT_DIR, "fernet.key")
    with open(path, "wb") as f:
        f.write(key)
    print("FERNET_KEY (base64) saved to:", path)
    print(key.decode())

def gen_rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(os.path.join(OUT_DIR, "rsa_private.pem"), "wb") as f:
        f.write(priv_pem)
    with open(os.path.join(OUT_DIR, "rsa_public.pem"), "wb") as f:
        f.write(pub_pem)
    print("RSA keys saved to:", OUT_DIR)

if __name__ == "__main__":
    gen_fernet_key()
    gen_rsa_keys()
    print("Done. انسخ قيمة FERNET_KEY وأضفها إلى Secrets في Replit أو إلى .env")
