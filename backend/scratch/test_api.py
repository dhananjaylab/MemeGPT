import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8000/api/memes/generate/quick', data=json.dumps({'prompt': 'when the wifi drops during a ranked match'}).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    print(urllib.request.urlopen(req).read())
except Exception as e:
    print(e.read().decode())
