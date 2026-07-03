import urllib.request, json

def post(endpoint, data):
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{endpoint}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())

# Test 1: Knowledge base question (should use notes + general knowledge)
print("=" * 60)
print("TEST 1: Notla ilgili soru (Not + Genel Bilgi)")
print("=" * 60)
result = post("/api/chat/graph", {"question": "Notlarimdaki DevOps araclari nelerdir ve Kubernetes nedir?", "top_k": 5})
print(f"Kaynaklar: {[s['title'] for s in result.get('sources', [])]}")
print(f"Cevap (ilk 350 karakter):")
print(result["answer"][:350])
print()

# Test 2: Pure general knowledge (no matching notes)
print("=" * 60)
print("TEST 2: Tamamen genel bilgi sorusu")
print("=" * 60)
result2 = post("/api/chat/graph", {"question": "Python'da async/await nedir? Basit bir ornek verir misin?", "top_k": 3})
print(f"Kaynaklar: {[s['title'] for s in result2.get('sources', [])]}")
print(f"Cevap (ilk 350 karakter):")
print(result2["answer"][:350])
print()

# Test 3: Casual conversation  
print("=" * 60)
print("TEST 3: Gundelik sohbet (hic not eslesmez)")
print("=" * 60)
result3 = post("/api/chat/graph", {"question": "Merhaba, bugun kendimi cok iyi hissediyorum. Sen nasilsin?", "top_k": 3})
print(f"Kaynaklar: {[s['title'] for s in result3.get('sources', [])]}")
print(f"Cevap (ilk 350 karakter):")
print(result3["answer"][:350])
print()

print("Tum hibrit chatbot testleri tamamlandi!")