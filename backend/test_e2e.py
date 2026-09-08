import urllib.request
import json
import urllib.parse
import sys

base_url = "http://localhost:8000/api"

# Login
data = urllib.parse.urlencode({"username": "test@test.com", "password": "password123"}).encode()
req = urllib.request.Request(f"{base_url}/auth/token", data=data)
try:
    with urllib.request.urlopen(req) as response:
        token = json.loads(response.read().decode()).get("access_token")
except Exception as e:
    print("Login failed, ensure user is registered.")
    sys.exit(1)

# Add API Key
req = urllib.request.Request(f"{base_url}/keys/", data=json.dumps({"provider_name": "groq", "key": "invalid-api-key-test"}).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as response:
    print("Added Key:", response.read().decode())

# Chat Request
req = urllib.request.Request(f"{base_url}/chat/", data=json.dumps({"provider": "groq", "message": "Hello!"}).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as response:
    print("Chat Stream:")
    for line in response:
        print(line.decode().strip())
