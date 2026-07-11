import httpx
r = httpx.get('http://localhost:8000/docs')
print(f"Status: {r.status_code}")
