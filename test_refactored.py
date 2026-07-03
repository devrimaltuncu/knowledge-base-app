import sys
sys.path.insert(0, "backend")

from database import get_all_notes, build_graph, USE_SUPABASE, get_all_tags

print(f"Storage mode: {'Supabase' if USE_SUPABASE else 'Local Filesystem'}")

notes = get_all_notes()
print(f"Total notes: {len(notes)}")
for n in notes:
    print(f"  [{n.id[:20]}] {n.title} | tags={n.tags} | links={n.links}")

graph = build_graph()
print(f"\nGraph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
for n in graph["nodes"]:
    print(f"  Node {n['id']}: {n['label']} [noteId={n['noteId'][:20]}]")
for e in graph["edges"]:
    print(f"  Edge: {e['source']} -> {e['target']}")

tags = get_all_tags()
print(f"\nTags: {tags}")

print("\nAll checks passed!")