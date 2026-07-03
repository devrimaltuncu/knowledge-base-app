import urllib.request, json

r = urllib.request.urlopen("http://127.0.0.1:8000/api/health")
print("Health:", json.loads(r.read()))

r2 = urllib.request.urlopen("http://127.0.0.1:8000/api/notes")
notes = json.loads(r2.read())
print(f"Notes from Supabase: {len(notes)}")
for n in notes:
    print(f"  {n['id'][:8]}... | {n['title']} | tags={n['tags']} | links={n['links']}")

r3 = urllib.request.urlopen("http://127.0.0.1:8000/api/graph")
graph = json.loads(r3.read())
print(f"\nGraph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

r4 = urllib.request.urlopen("http://127.0.0.1:8000/api/tags")
tags = json.loads(r4.read())
print(f"Tags: {tags['tags']}")

print("\nAll Supabase API tests passed!")