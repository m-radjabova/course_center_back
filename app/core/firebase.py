import os
import json
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()


def get_firebase_credentials():
    credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if credentials_json:
        return credentials.Certificate(json.loads(credentials_json))

    path = os.getenv("FIREBASE_CREDENTIALS")
    if path:
        return credentials.Certificate(path)

    firebase_env = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": (os.getenv("FIREBASE_PRIVATE_KEY") or "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
    }

    missing = [key for key, value in firebase_env.items() if not value]
    if missing:
        missing_keys = ", ".join(missing)
        raise ValueError(
            "Firebase configuration is incomplete. Set FIREBASE_CREDENTIALS_JSON, "
            f"FIREBASE_CREDENTIALS, or these env vars: {missing_keys}"
        )

    return credentials.Certificate(firebase_env)


cred = get_firebase_credentials()
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
