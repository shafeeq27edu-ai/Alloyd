import urllib.request
import json
import urllib.parse

base_url = "http://localhost:8000/api"

try:
    req = urllib.request.Request(f"{base_url}/auth/register", data=json.dumps({"email": "test@test.com", "password": "password123"}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        print("Register:", response.status, response.read().decode())
except urllib.error.HTTPError as e:
    print("Register failed:", e.code, e.read().decode())

try:
    data = urllib.parse.urlencode({"username": "test@test.com", "password": "password123"}).encode()
    req2 = urllib.request.Request(f"{base_url}/auth/token", data=data)
    with urllib.request.urlopen(req2) as response:
        resp_data = response.read().decode()
        print("Login:", response.status, resp_data)
        token = json.loads(resp_data).get("access_token")
        
        req3 = urllib.request.Request(f"{base_url}/auth/me", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req3) as r3:
            print("Me:", r3.status, r3.read().decode())
except urllib.error.HTTPError as e:
    print("Failed:", e.code, e.read().decode())
