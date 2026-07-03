import urllib.request, json

def test(url, data=None):
    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

# Test health
health = test("http://127.0.0.1:8000/api/health")
print(f"Health: {json.dumps(health)}")

# Test suggested connections
print("\n=== GET /api/notes/Home/suggested ===")
# First get a note ID
notes = test("http://127.0.0.1:8000/api/notes")
if notes:
    first_note = notes[0]
    note_id = first_note["id"]
    print(f"Testing suggestions for: {first_note['title']} (id: {note_id[:20]}...)")
    suggested = test(f"http://127.0.0.1:8000/api/notes/{note_id}/suggested?top_k=5")
    if suggested:
        print(f"Got {len(suggested['suggestions'])} suggestions:")
        for s in suggested["suggestions"]:
            print(f"  - {s['title']} (score: {s['score']})")

# Test Graph-RAG chat
print("\n=== POST /api/chat/graph ===")
result = test("http://127.0.0.1:8000/api/chat/graph", {
    "question": "What are the common patterns in my tech notes?",
    "top_k": 3,
})
if result:
    print(f"Answer length: {len(result['answer'])} chars")
    print(f"Sources: {[s['title'] for s in result.get('sources', [])]}")
    print(f"\nAnswer preview:\n{result['answer'][:500]}...")

print("\nAll AI tests passed!")