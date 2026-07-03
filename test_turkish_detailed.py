import urllib.request, json, sys

# Add backend to path to test tokenizer directly
sys.path.insert(0, "backend")
from embeddings import _simple_tokenize, _normalize_turkish

def post(endpoint, data):
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{endpoint}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())

# Test tokenizer
print("=== Tokenizer Test ===")
query_tr = "Makine ogrenmesi notlarimda hangi algoritmalardan bahsediliyor?"
tokens = _simple_tokenize(query_tr)
print(f"Original: {query_tr}")
print(f"Tokens:   {tokens}")
print(f"Contains 'machine': {'machine' in tokens}")
print(f"Contains 'learning': {'learning' in tokens}")
print(f"Contains 'algorithm': {'algorithm' in tokens}")

# Test query normalization
normalized = _normalize_turkish(query_tr)
print(f"Normalized: {normalized}")
print()

# Test the actual API
print("=== API Test 1: Turkish ML query ===")
result = post("/api/chat/graph", {
    "question": "Makine ogrenmesi notlarimda hangi algoritmalardan bahsediliyor?",
    "top_k": 5,
})
print(f"Sources found: {len(result.get('sources', []))}")
for s in result.get("sources", []):
    print(f"  - {s['title']} (score: {s['score']})")
print(f"Answer starts with: {result['answer'][:200]}")
print()

# Test a simpler Turkish query
print("=== API Test 2: Simple Turkish word match ===")
result2 = post("/api/chat/graph", {
    "question": "proje mimari",
    "top_k": 3,
})
print(f"Sources found: {len(result2.get('sources', []))}")
for s in result2.get("sources", []):
    print(f"  - {s['title']} (score: {s['score']})")
print(f"Answer starts with: {result2['answer'][:200]}")