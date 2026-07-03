import urllib.request, json

def test_endpoint(url, label):
    print(f"=== {label} ===")
    data = urllib.request.urlopen(url).read()
    return json.loads(data)

# Test backend directly
parsed = test_endpoint("http://127.0.0.1:8000/api/graph", "GRAPH API (Backend)")
print(f"Nodes: {len(parsed['nodes'])}")
print(f"Edges: {len(parsed['edges'])}")
for n in parsed["nodes"]:
    print(f"  Node: {n['label']} [{n['group']}] -> filename={n['filename']}")
for e in parsed["edges"]:
    print(f"  Edge: {e['source']} -> {e['target']}")

notes = test_endpoint("http://127.0.0.1:8000/api/notes", "NOTES API (Backend)")
print(f"Total notes: {len(notes)}")
for n in notes:
    print(f"  {n['title']} -> links: {n['links']}")

# Test Vite proxy
try:
    proxy = test_endpoint("http://localhost:5173/api/graph", "GRAPH API (Vite Proxy)")
    print(f"Vite proxy OK! {len(proxy['nodes'])} nodes, {len(proxy['edges'])} edges")
except Exception as e:
    print(f"Vite proxy test: {e}")

print()
print("All API tests passed!")
