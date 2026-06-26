import requests
from requests.auth import HTTPBasicAuth

UNISMS_SECRET_KEY = "sk_1d6c9ca4-841a-45d0-971d-83353750a916"


def send_sms(phone, message):
    url = "https://unismsapi.com/api/sms"

    try:
        response = requests.post(
            url,
            json={
                "recipient": phone,
                "content": message
            },
            auth=HTTPBasicAuth(UNISMS_SECRET_KEY, ""),
            headers={
                "Content-Type": "application/json"
            },
            timeout=30
        )

        print("=" * 60)
        print("UNISMS RESPONSE")
        print("Status Code :", response.status_code)
        print("Response    :", response.text)
        print("=" * 60)

        if response.status_code in [200, 201]:
            print("✅ SMS SENT SUCCESSFULLY")
        else:
            print("❌ SMS FAILED")

        try:
            return response.json()
        except ValueError:
            return {
                "success": False,
                "status": response.status_code,
                "raw": response.text
            }

    except requests.exceptions.RequestException as e:
        print("=" * 60)
        print("❌ CONNECTION ERROR")
        print(e)
        print("=" * 60)

        return {
            "success": False,
            "error": str(e)
        }