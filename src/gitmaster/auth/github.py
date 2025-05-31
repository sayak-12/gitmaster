import requests
import time
import keyring
import webbrowser
from dotenv import load_dotenv

load_dotenv()
GITHUB_CLIENT_ID = "Ov23lijg7La1rbLPdZWl" 
CLIENT_ID = GITHUB_CLIENT_ID
TOKEN_SERVICE = "gitmaster"
TOKEN_USERNAME = "github_token"
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
HEADERS = {"Accept": "application/json"}

def save_token(token):
    keyring.set_password(TOKEN_SERVICE, TOKEN_USERNAME, token)

def get_token():
    return keyring.get_password(TOKEN_SERVICE, TOKEN_USERNAME)

def delete_token():
    keyring.delete_password(TOKEN_SERVICE, TOKEN_USERNAME)

def login():
    # Step 1: Get device & user code
    data = {
        "client_id": CLIENT_ID,
        "scope": "repo"
    }
    resp = requests.post(DEVICE_CODE_URL, data=data, headers=HEADERS)
    resp.raise_for_status()
    device_data = resp.json()

    print("\n🔐 GitHub Login")
    print("👉 Open this URL in your browser:")
    print(f"   {device_data['verification_uri']}")
    print(f"🔑 And enter this code: {device_data['user_code']}\n")

    # Auto-open in browser
    webbrowser.open(device_data["verification_uri"], new=2)

    # Step 2: Poll for access token
    while True:
        time.sleep(device_data["interval"])
        token_data = {
            "client_id": CLIENT_ID,
            "device_code": device_data["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }
        token_resp = requests.post(ACCESS_TOKEN_URL, data=token_data, headers=HEADERS)
        token_json = token_resp.json()

        if "access_token" in token_json:
            save_token(token_json["access_token"])
            print("✅ Login successful!")
            return

        elif token_json.get("error") == "authorization_pending":
            continue

        elif token_json.get("error") == "slow_down":
            time.sleep(5)
            continue

        else:
            print(f"❌ Login failed: {token_json.get('error_description')}")
            return

def logout():
    delete_token()
    print("🧼 Logged out.")
