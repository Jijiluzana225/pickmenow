
import requests
from requests.auth import HTTPBasicAuth

UNISMS_SECRET_KEY = "sk_1d6c9ca4-841a-45d0-971d-83353750a916"
SENDER_ID = "UnisoftDEV"   # Your approved Sender ID


def send_sms(phone, message):
    url = "https://unismsapi.com/api/sms"

    payload = {
        "recipient": phone,
        "content": message,
        "sender_id": SENDER_ID
    }

    response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(UNISMS_SECRET_KEY, ""),
        headers={
            "Content-Type": "application/json"
        }
    )

    print("Status:", response.status_code)
    print("Raw:", response.text)

    try:
        return response.json()
    except Exception:
        return {
            "error": "Not JSON response",
            "raw": response.text
        }