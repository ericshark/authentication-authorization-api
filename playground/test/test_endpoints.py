import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, path, data=None, params=""):
    url = f"{BASE_URL}{path}{params}"
    headers = {'Content-Type': 'application/json'}
    req_data = json.dumps(data).encode('utf-8') if data else None
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req) as response:
            print(f"[{method.upper()}] {path}{params} -> {response.status}")
    except urllib.error.HTTPError as e:
        print(f"[{method.upper()}] {path}{params} -> ERROR {e.code}: {e.read().decode('utf-8')[:200]}")
    except Exception as e:
        print(f"[{method.upper()}] {path}{params} -> ERROR {e}")

print("Testing Endpoints...")

# 1. Root
test_endpoint('GET', '/')

# 2. GET users
test_endpoint('GET', '/users/app')

# 3. Create user
user_payload = {
    "username": "testuser",
    "name": "Test User",
    "email": "test@example.com",
    "password": "password123"
}
test_endpoint('POST', '/users/createUser', data=user_payload)

# 4. Get User
test_endpoint('GET', '/users/getUser/1')

# 5. Update Name
test_endpoint('POST', '/users/updateName', params="?name=NewName&user_id=1")

# 6. Update User (PUT)
test_endpoint('PUT', '/usersupdate-user/1', data=user_payload)

# 7. Patch empty endpoint
test_endpoint('PATCH', '/users/update/1', params="?name=PatchedName")

# 8. Auth empty endpoint
test_endpoint('POST', '/auth/')

