import urllib.request
import json
import urllib.parse
import sys

base_url = "http://localhost:8000/api"

# Register new user
req = urllib.request.Request(f"{base_url}/auth/register", data=json.dumps({"email": "test@test.com", "password": "password123"}).encode(), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        cookie_header = response.headers.get('Set-Cookie')
        cookie = cookie_header.split(';')[0] if cookie_header else None
except urllib.error.HTTPError as e:
    # If already registered, login
    data = urllib.parse.urlencode({"username": "test@test.com", "password": "password123"}).encode()
    req = urllib.request.Request(f"{base_url}/auth/token", data=data)
    with urllib.request.urlopen(req) as response:
        cookie_header = response.headers.get('Set-Cookie')
        cookie = cookie_header.split(';')[0] if cookie_header else None

# Add API Key
req = urllib.request.Request(f"{base_url}/keys/", data=json.dumps({"provider_name": "groq", "key": "invalid-api-key-test"}).encode(), headers={"Content-Type": "application/json", "Cookie": cookie})
with urllib.request.urlopen(req) as response:
    print("Added Key:", response.read().decode())

# Chat Request - Auto Mode
print("Testing Auto Mode...")
req = urllib.request.Request(f"{base_url}/chat/", data=json.dumps({"mode": "auto", "message": "Hello!"}).encode(), headers={"Content-Type": "application/json", "Cookie": cookie})
with urllib.request.urlopen(req) as response:
    print("Chat Stream (Auto):")
    for line in response:
        print(line.decode().strip())

# Chat Request - Manual Mode
print("\nTesting Manual Mode...")
req = urllib.request.Request(f"{base_url}/chat/", data=json.dumps({"mode": "manual", "provider": "groq", "model": "llama3-8b-8192", "message": "Hello!"}).encode(), headers={"Content-Type": "application/json", "Cookie": cookie})
with urllib.request.urlopen(req) as response:
    print("Chat Stream (Manual):")
    for line in response:
        print(line.decode().strip())
