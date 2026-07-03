"""
Print the SQL DDL needed to initialize the Supabase database.
Copy-paste this into: Supabase Dashboard → SQL Editor → New Query → Run
"""
import sys
sys.path.insert(0, "backend")
from database import SCHEMA_SQL

print("=" * 60)
print("  COPY THIS ENTIRE SQL TO SUPABASE SQL EDITOR")
print("=" * 60)
print()
print("1. Go to: https://supabase.com/dashboard/project/yykkduhwqfarzaywktdg/sql/new")
print("2. Paste the SQL below")
print("3. Click 'Run'")
print("4. Then run: python migrate_local_to_supabase.py")
print()
print("=" * 60)
print(SCHEMA_SQL)
print("=" * 60)