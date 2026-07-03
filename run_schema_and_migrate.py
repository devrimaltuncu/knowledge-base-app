"""
Step 1: Print the SQL DDL for the user to paste into Supabase SQL Editor (one-time)
Step 2: After the user confirms, run the migration to upload local .md files
"""
import sys, os, webbrowser
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")

sys.path.insert(0, "backend")
from database import SCHEMA_SQL

SUPABASE_PROJECT = "yykkduhwqfarzaywktdg"
SQL_EDITOR_URL = f"https://supabase.com/dashboard/project/{SUPABASE_PROJECT}/sql/new"

print("=" * 70)
print("  STEP 1: Initialize Database Schema")
print("=" * 70)
print()
print("Opening the Supabase SQL Editor in your browser...")
webbrowser.open(SQL_EDITOR_URL)
print()
print("Copy and paste the SQL below into the SQL Editor and click 'Run'.")
print()
print("=" * 70)
print(SCHEMA_SQL)
print("=" * 70)
print()
input("Press ENTER after you've run the SQL in Supabase to continue with migration...")
print()

# Step 2: Run migration
print("=" * 70)
print("  STEP 2: Migrate Local Notes to Supabase")
print("=" * 70)
print()

from backend.migrate_local_to_supabase import migrate
migrate()