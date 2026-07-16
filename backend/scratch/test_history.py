import requests
import sys

print("Logging in...")
login_url = "http://localhost:8000/api/v1/auth/login"
res = requests.post(login_url, json={"email": "admin@redactai.in", "password": "Admin@123456"})
if res.status_code != 200:
    print(f"Login failed: {res.status_code}")
    sys.exit(1)
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login successful.")

print("\nFetching /api/v1/legal/quality...")
try:
    q_res = requests.get("http://localhost:8000/api/v1/legal/quality", headers=headers, timeout=5)
    print(f"Status: {q_res.status_code}")
    print(f"Response: {q_res.json()}")
except Exception as e:
    print(f"Error: {e}")

print("\nFetching /api/v1/legal/prompts...")
try:
    p_res = requests.get("http://localhost:8000/api/v1/legal/prompts", headers=headers, timeout=5)
    print(f"Status: {p_res.status_code}")
    print(f"Response: {p_res.json()}")
except Exception as e:
    print(f"Error: {e}")
