import urllib.request, json
resp = urllib.request.urlopen('http://0.0.0.0:8001/health')
print(json.load(resp))
