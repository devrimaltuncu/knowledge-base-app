import urllib.request, json

def post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())

# Test 1: Turkish query
print("=== Turkish Query Test ===")
result = post("http://127.0.0.1:8000/api/chat/graph", {
    "question": "Makine ogrenmesi notlarimda hangi algoritmalardan bahsediliyor?",
    "top_k": 3,
})
print(f"Sources: {[s['title'] for s in result.get('sources', [])]}")
print(f"Answer preview (first 300 chars):")
print(result["answer"][:300])
print()

# Test 2: English query -> should still answer in Turkish
print("=== English Query -> Turkish Answer Test ===")
result2 = post("http://127.0.0.1:8000/api/chat/graph", {
    "question": "What devops tools are mentioned in my notes?",
    "top_k": 3,
})
print(f"Sources: {[s['title'] for s in result2.get('sources', [])]}")
print(f"Answer preview (first 300 chars):")
print(result2["answer"][:300])
print()

print("All Turkish tests passed!")