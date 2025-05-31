import keyring

SERVICE_NAME = "gitmaster"
OPENAI_KEY_NAME = "openai_api_key"

def save_openai_key(key: str):
    keyring.set_password(SERVICE_NAME, OPENAI_KEY_NAME, key)

def get_openai_key() -> str | None:
    return keyring.get_password(SERVICE_NAME, OPENAI_KEY_NAME)

def delete_openai_key():
    keyring.delete_password(SERVICE_NAME, OPENAI_KEY_NAME)
