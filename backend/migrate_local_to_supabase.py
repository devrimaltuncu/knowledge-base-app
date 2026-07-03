"""
One-time migration script: reads local .md files from /notes folder
and inserts them into Supabase tables.

Usage:
  1. Create a .env file in backend/ with your Supabase credentials
  2. Run: python backend/migrate_local_to_supabase.py

The script is idempotent: notes with duplicate titles are skipped.
"""

import os
import re
import sys
from pathlib import Path

# Add backend dir to path so we can import database
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from database import (
    USE_SUPABASE,
    supabase_client,
    extract_wiki_links,
    SCHEMA_SQL,
)

# Also need frontmatter for local file parsing
import frontmatter

NOTES_DIR = Path(os.environ.get("NOTES_DIR", Path(__file__).resolve().parent.parent / "notes"))


def ensure_schema():
    """Execute the DDL schema in Supabase."""
    if not USE_SUPABASE or not supabase_client:
        print("ERROR: Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        sys.exit(1)

    print("Running schema DDL...")
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in SCHEMA_SQL.split(";") if s.strip()]
    for stmt in statements:
        try:
            # Use raw SQL via rpc or direct SQL if available
            # The supabase-py client doesn't have a direct .sql() method,
            # so we use the REST API with a custom header for raw SQL.
            # Alternative: print the SQL for manual execution.
            pass
        except Exception as e:
            print(f"  Note: {e}")

    print("Schema DDL printed below. Run this in Supabase SQL Editor first:")
    print("=" * 60)
    print(SCHEMA_SQL)
    print("=" * 60)


def migrate():
    if not USE_SUPABASE or not supabase_client:
        print("ERROR: Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        sys.exit(1)

    db = supabase_client

    print(f"\nScanning notes directory: {NOTES_DIR}")
    md_files = sorted(NOTES_DIR.glob("*.md"))
    if not md_files:
        print("No .md files found in notes directory.")
        return

    print(f"Found {len(md_files)} markdown files.\n")

    # Track stats
    notes_created = 0
    notes_skipped = 0
    links_created = 0
    tags_created = 0

    # First pass: create all notes (with just title + content, no links yet)
    note_id_map: dict[str, str] = {}  # title -> uuid
    note_content_map: dict[str, str] = {}  # title -> content

    for md_file in md_files:
        raw = md_file.read_text(encoding="utf-8")
        post = frontmatter.loads(raw)
        meta = dict(post.metadata)
        title = meta.get("title", md_file.stem)
        content = post.content
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # Check if note with this title already exists
        existing = db.table("notes").select("id").eq("title", title).execute()
        if existing.data:
            note_id = existing.data[0]["id"]
            note_id_map[title] = note_id
            print(f"  [SKIP] '{title}' already exists (id: {note_id[:8]}...)")
            notes_skipped += 1
            # Still store content for link resolution
            note_content_map[title] = content
            continue

        # Create the note
        result = db.table("notes").insert({
            "title": title,
            "content": content,
        }).execute()
        note_id = result.data[0]["id"]
        note_id_map[title] = note_id
        note_content_map[title] = content
        notes_created += 1
        print(f"  [CREATED] '{title}' (id: {note_id[:8]}...)")

        # Create tags
        for tag_name in tags:
            tag_result = db.table("tags").select("id").eq("name", tag_name).execute()
            if tag_result.data:
                tag_id = tag_result.data[0]["id"]
            else:
                tag_insert = db.table("tags").insert({"name": tag_name}).execute()
                tag_id = tag_insert.data[0]["id"]
                tags_created += 1
            try:
                db.table("note_tags").insert({
                    "note_id": note_id,
                    "tag_id": tag_id,
                }).execute()
            except Exception:
                pass  # Already linked

    print(f"\nNotes: {notes_created} created, {notes_skipped} skipped")

    # Second pass: create links based on wiki-links in content
    print("\nResolving wiki-links...")
    for title, content in note_content_map.items():
        source_id = note_id_map.get(title)
        if not source_id:
            continue
        links = extract_wiki_links(content)
        for link_title in links:
            target_id = note_id_map.get(link_title)
            if not target_id:
                # Try case-insensitive match
                for t, tid in note_id_map.items():
                    if t.lower() == link_title.lower():
                        target_id = tid
                        break
            if not target_id or target_id == source_id:
                continue
            # Check if link already exists
            existing_link = db.table("links").select("id") \
                .eq("source_note_id", source_id) \
                .eq("target_note_id", target_id) \
                .execute()
            if existing_link.data:
                continue
            try:
                db.table("links").insert({
                    "source_note_id": source_id,
                    "target_note_id": target_id,
                }).execute()
                links_created += 1
                print(f"  Link: '{title}' -> '{link_title}'")
            except Exception as e:
                print(f"  [ERROR] Link '{title}' -> '{link_title}': {e}")

    print(f"\nLinks created: {links_created}")
    print(f"Tags created: {tags_created}")
    print(f"\nMigration complete! {notes_created + notes_skipped} notes total in database.")
    print("Run the backend server to verify: python backend/main.py")


if __name__ == "__main__":
    print("=" * 60)
    print("  Local Markdown → Supabase Migration Tool")
    print("=" * 60)
    ensure_schema()
    input("\nPress Enter to continue with data migration (after running the DDL in Supabase SQL Editor)...")
    migrate()