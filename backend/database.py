"""
Database module: Supabase client, schema initialization, and query functions.
Supports both Supabase (cloud, multi-user) and local filesystem fallback modes.
All Supabase queries accept an optional user_id for multi-tenant scoping.
"""

import os
import re
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import frontmatter
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(Path(__file__).resolve().parent / ".env")

# ---------- Configuration ----------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
NOTES_DIR = Path(os.environ.get("NOTES_DIR", Path(__file__).resolve().parent.parent / "notes"))

USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

supabase_client = None
if USE_SUPABASE:
    from supabase import create_client, Client
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ---------- Schema DDL (run once via Supabase SQL Editor or migration) ----------
SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Core notes table
CREATE TABLE IF NOT EXISTS notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID DEFAULT auth.uid(),
    title       TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    embedding   vector(1536),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tags dictionary
CREATE TABLE IF NOT EXISTS tags (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL
);

-- Many-to-many note <-> tag
CREATE TABLE IF NOT EXISTS note_tags (
    note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    tag_id  UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

-- Materialized wiki-link edges
CREATE TABLE IF NOT EXISTS links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_note_id  UUID REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id  UUID REFERENCES notes(id) ON DELETE CASCADE,
    UNIQUE(source_note_id, target_note_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_note_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_note_id);
CREATE INDEX IF NOT EXISTS idx_note_tags_note ON note_tags(note_id);
CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag_id);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_notes_updated_at ON notes;
CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE note_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE links ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY "Users can view own notes" ON notes
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own notes" ON notes
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own notes" ON notes
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own notes" ON notes
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own note_tags" ON note_tags
    FOR SELECT USING (EXISTS (SELECT 1 FROM notes WHERE notes.id = note_tags.note_id AND notes.user_id = auth.uid()));
CREATE POLICY "Users can insert own note_tags" ON note_tags
    FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM notes WHERE notes.id = note_tags.note_id AND notes.user_id = auth.uid()));
CREATE POLICY "Users can delete own note_tags" ON note_tags
    FOR DELETE USING (EXISTS (SELECT 1 FROM notes WHERE notes.id = note_tags.note_id AND notes.user_id = auth.uid()));

CREATE POLICY "Users can view own links" ON links
    FOR SELECT USING (EXISTS (SELECT 1 FROM notes WHERE notes.id = links.source_note_id AND notes.user_id = auth.uid()));
CREATE POLICY "Users can insert own links" ON links
    FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM notes WHERE notes.id = links.source_note_id AND notes.user_id = auth.uid()));
CREATE POLICY "Users can delete own links" ON links
    FOR DELETE USING (EXISTS (SELECT 1 FROM notes WHERE notes.id = links.source_note_id AND notes.user_id = auth.uid()));
"""


# ---------- Data Models ----------
@dataclass
class NoteData:
    id: str = ""
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "links": self.links,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------- Wiki Link Parser ----------
WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def extract_wiki_links(content: str) -> list[str]:
    raw = WIKI_LINK_RE.findall(content)
    seen = set()
    result = []
    for link in raw:
        trimmed = link.strip()
        if trimmed and trimmed not in seen:
            seen.add(trimmed)
            result.append(trimmed)
    return result


# ---------- Local Filesystem Mode (Fallback) ----------
def _scan_local_notes() -> list[NoteData]:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    notes = []
    for md_file in sorted(NOTES_DIR.glob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
            post = frontmatter.loads(raw)
            meta = dict(post.metadata)
            title = meta.get("title", md_file.stem)
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            content = post.content
            links = extract_wiki_links(content)
            notes.append(NoteData(
                id=md_file.stem, title=title, content=content,
                tags=tags, links=links,
                created_at=str(md_file.stat().st_ctime),
                updated_at=str(md_file.stat().st_mtime),
            ))
        except Exception as e:
            print(f"Warning: Could not parse {md_file}: {e}")
    return notes


def _save_local_note(note_id: str, content: str) -> Optional[NoteData]:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = NOTES_DIR / f"{note_id}.md"
    if not filepath.exists():
        return None
    raw = filepath.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    meta = dict(post.metadata)
    if meta:
        new_raw = frontmatter.dumps(frontmatter.Post(content, **meta))
    else:
        new_raw = content
    filepath.write_text(new_raw, encoding="utf-8")
    title = meta.get("title", note_id)
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    links = extract_wiki_links(content)
    return NoteData(id=note_id, title=title, content=content, tags=tags, links=links)


def _delete_local_note(note_id: str) -> bool:
    filepath = NOTES_DIR / f"{note_id}.md"
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def _build_graph_local(notes: list[NoteData]) -> dict:
    nodes, edges = [], []
    stem_to_idx = {}
    seen_edges = set()
    for i, note in enumerate(notes):
        nid = str(i)
        stem_to_idx[note.id] = nid
        nodes.append({"id": nid, "label": note.title, "noteId": note.id, "tags": note.tags, "group": note.tags[0] if note.tags else "untagged"})
    for note in notes:
        src = stem_to_idx.get(note.id)
        if src is None: continue
        for link_target in note.links:
            tgt = stem_to_idx.get(link_target)
            if tgt is None:
                for stem, nid in stem_to_idx.items():
                    if stem.lower() == link_target.lower():
                        tgt = nid; break
            if tgt is None or tgt == src: continue
            key = tuple(sorted((src, tgt)))
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"source": src, "target": tgt})
    return {"nodes": nodes, "edges": edges}


# ---------- Supabase Mode ----------
def _db_get_client():
    if not supabase_client:
        raise RuntimeError("Supabase client is not configured")
    return supabase_client


def _db_get_all_notes(user_id: Optional[str] = None) -> list[NoteData]:
    db = _db_get_client()
    query = db.table("notes").select("*").order("created_at", desc=False)
    if user_id:
        query = query.eq("user_id", user_id)
    result = query.execute()
    note_map = {}
    note_ids = []
    for row in result.data:
        nd = NoteData(id=row["id"], title=row["title"], content=row.get("content",""),
                      created_at=str(row.get("created_at","")), updated_at=str(row.get("updated_at","")))
        note_map[nd.id] = nd
        note_ids.append(nd.id)
    if not note_ids: return []
    tag_rows = db.table("note_tags").select("note_id, tags(name)").in_("note_id", note_ids).execute()
    for tr in tag_rows.data:
        nd = note_map.get(tr["note_id"])
        if nd and tr.get("tags"):
            tn = tr["tags"]["name"] if isinstance(tr["tags"], dict) else tr["tags"]
            if tn: nd.tags.append(tn)
    link_rows = db.table("links").select("source_note_id, target_note_id, target:notes!links_target_note_id_fkey(title)").in_("source_note_id", note_ids).execute()
    for lr in link_rows.data:
        nd = note_map.get(lr["source_note_id"])
        if nd and lr.get("target"):
            tt = lr["target"]["title"] if isinstance(lr["target"], dict) else lr["target"]
            nd.links.append(tt)
    return [note_map[nid] for nid in note_ids]


def _db_get_note(note_id: str, user_id: Optional[str] = None) -> Optional[NoteData]:
    db = _db_get_client()
    query = db.table("notes").select("*").eq("id", note_id)
    if user_id: query = query.eq("user_id", user_id)
    result = query.execute()
    if not result.data: return None
    row = result.data[0]
    nd = NoteData(id=row["id"], title=row["title"], content=row.get("content",""),
                  created_at=str(row.get("created_at","")), updated_at=str(row.get("updated_at","")))
    for tr in db.table("note_tags").select("tags(name)").eq("note_id", note_id).execute().data:
        tn = tr["tags"]["name"] if isinstance(tr["tags"], dict) else tr["tags"]
        if tn: nd.tags.append(tn)
    for lr in db.table("links").select("target_note_id, target:notes!links_target_note_id_fkey(title)").eq("source_note_id", note_id).execute().data:
        if lr.get("target"):
            tt = lr["target"]["title"] if isinstance(lr["target"], dict) else lr["target"]
            nd.links.append(tt)
    return nd


def _db_create_note(title: str, content: str = "", user_id: Optional[str] = None) -> NoteData:
    db = _db_get_client()
    row = {"title": title, "content": content}
    if user_id: row["user_id"] = user_id
    result = db.table("notes").insert(row).execute()
    note_id = result.data[0]["id"]
    _db_sync_tags_and_links(note_id, content)
    return _db_get_note(note_id, user_id)


def _db_update_note(note_id: str, content: str, user_id: Optional[str] = None) -> Optional[NoteData]:
    db = _db_get_client()
    query = db.table("notes").update({"content": content}).eq("id", note_id)
    if user_id: query = query.eq("user_id", user_id)
    result = query.execute()
    if not result.data: return None
    _db_sync_tags_and_links(note_id, content)
    return _db_get_note(note_id, user_id)


def _db_delete_note(note_id: str, user_id: Optional[str] = None) -> bool:
    db = _db_get_client()
    query = db.table("notes").delete().eq("id", note_id)
    if user_id: query = query.eq("user_id", user_id)
    result = query.execute()
    return len(result.data) > 0


def _db_sync_tags_and_links(note_id: str, content: str):
    db = _db_get_client()
    wiki_links = extract_wiki_links(content)
    db.table("links").delete().eq("source_note_id", note_id).execute()
    for link_title in wiki_links:
        tr = db.table("notes").select("id").eq("title", link_title).execute()
        if not tr.data:
            tr = db.table("notes").select("id").ilike("title", link_title).execute()
        if tr.data:
            tid = tr.data[0]["id"]
            if tid != note_id:
                try: db.table("links").insert({"source_note_id": note_id, "target_note_id": tid}).execute()
                except Exception: pass
    hashtag_re = re.compile(r'(?:^|\s)#([a-zA-Z0-9_\-\u0400-\u04FF]+)')
    tag_names = set(t.strip() for t in hashtag_re.findall(content))
    if tag_names:
        db.table("note_tags").delete().eq("note_id", note_id).execute()
        for tname in tag_names:
            tr = db.table("tags").select("id").eq("name", tname).execute()
            tid = tr.data[0]["id"] if tr.data else db.table("tags").insert({"name": tname}).execute().data[0]["id"]
            try: db.table("note_tags").insert({"note_id": note_id, "tag_id": tid}).execute()
            except Exception: pass


def _db_build_graph(user_id: Optional[str] = None) -> dict:
    db = _db_get_client()
    query = db.table("notes").select("id, title").order("created_at", desc=False)
    if user_id: query = query.eq("user_id", user_id)
    notes_result = query.execute()
    note_list = notes_result.data
    id_to_idx = {}
    nodes = []
    for i, n in enumerate(note_list):
        idx = str(i)
        id_to_idx[n["id"]] = idx
        tags = []
        for tr in db.table("note_tags").select("tags(name)").eq("note_id", n["id"]).execute().data:
            tn = tr["tags"]["name"] if isinstance(tr["tags"], dict) else tr["tags"]
            if tn: tags.append(tn)
        nodes.append({"id": idx, "label": n["title"], "noteId": n["id"], "tags": tags, "group": tags[0] if tags else "untagged"})
    edges, seen = [], set()
    for lr in db.table("links").select("source_note_id, target_note_id").execute().data:
        src, tgt = id_to_idx.get(lr["source_note_id"]), id_to_idx.get(lr["target_note_id"])
        if src is None or tgt is None or src == tgt: continue
        key = tuple(sorted((src, tgt)))
        if key not in seen:
            seen.add(key)
            edges.append({"source": src, "target": tgt})
    return {"nodes": nodes, "edges": edges}


# ---------- Unified API ----------
def get_all_notes(user_id: Optional[str] = None) -> list[NoteData]:
    if USE_SUPABASE: return _db_get_all_notes(user_id)
    return _scan_local_notes()


def get_note(note_id: str, user_id: Optional[str] = None) -> Optional[NoteData]:
    if USE_SUPABASE: return _db_get_note(note_id, user_id)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = NOTES_DIR / f"{note_id}.md"
    if not filepath.exists(): return None
    raw = filepath.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    meta = dict(post.metadata)
    title = meta.get("title", filepath.stem)
    tags = meta.get("tags", [])
    if isinstance(tags, str): tags = [t.strip() for t in tags.split(",") if t.strip()]
    links = extract_wiki_links(post.content)
    return NoteData(id=filepath.stem, title=title, content=post.content, tags=tags, links=links,
                     created_at=str(filepath.stat().st_ctime), updated_at=str(filepath.stat().st_mtime))


def create_note(title: str, content: str = "", user_id: Optional[str] = None) -> NoteData:
    if USE_SUPABASE: return _db_create_note(title, content, user_id)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    stem = title.replace(" ", "-").lower()
    filepath = NOTES_DIR / f"{stem}.md"
    if filepath.exists(): raise FileExistsError(f"Note already exists: {stem}")
    filepath.write_text(content, encoding="utf-8")
    return NoteData(id=stem, title=title, content=content, links=extract_wiki_links(content))


def update_note(note_id: str, content: str, user_id: Optional[str] = None) -> Optional[NoteData]:
    if USE_SUPABASE: return _db_update_note(note_id, content, user_id)
    return _save_local_note(note_id, content)


def delete_note(note_id: str, user_id: Optional[str] = None) -> bool:
    if USE_SUPABASE: return _db_delete_note(note_id, user_id)
    return _delete_local_note(note_id)


def build_graph(user_id: Optional[str] = None) -> dict:
    if USE_SUPABASE: return _db_build_graph(user_id)
    return _build_graph_local(_scan_local_notes())


def get_all_tags(user_id: Optional[str] = None) -> list[str]:
    if USE_SUPABASE:
        db = _db_get_client()
        result = db.table("tags").select("name").order("name").execute()
        return [r["name"] for r in result.data]
    tag_set = set()
    for n in _scan_local_notes():
        for t in n.tags: tag_set.add(t)
    return sorted(tag_set)