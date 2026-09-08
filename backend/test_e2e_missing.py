import urllib.request
import json
import urllib.parse
import sys

base_url = "http://localhost:8000/api"

# Register new user
req = urllib.request.Request(f"{base_url}/auth/register", data=json.dumps({"email": "test2@test.com", "password": "password123"}).encode(), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        token = json.loads(response.read().decode()).get("access_token")
except urllib.error.HTTPError as e:
    # If already registered, login
    data = urllib.parse.urlencode({"username": "test2@test.com", "password": "password123"}).encode()
    req = urllib.request.Request(f"{base_url}/auth/token", data=data)
    with urllib.request.urlopen(req) as response:
        token = json.loads(response.read().decode()).get("access_token")

# Chat Request (No API key added for test2@test.com)
try:
    req = urllib.request.Request(f"{base_url}/chat/", data=json.dumps({"provider": "groq", "message": "Hello!"}).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as response:
        print("Chat Stream:")
        for line in response:
            print(line.decode().strip())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode())
