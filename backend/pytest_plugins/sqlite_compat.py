"""
Pytest plugin to make PostgreSQL-specific SQLAlchemy types work with SQLite.

This plugin patches JSONB and ARRAY types BEFORE any model modules are imported.
It must be loaded first via pytest_plugins in conftest.py or pytest.ini.
"""
from sqlalchemy import JSON

# Patch PostgreSQL dialect types
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import json as pg_json

# Save originals (only once)
if not hasattr(postgresql, '_patched_for_sqlite'):
    postgresql._original_jsonb = postgresql.JSONB
    postgresql._original_array = postgresql.ARRAY

    # Replace with JSON
    postgresql.JSONB = JSON
    postgresql.ARRAY = lambda *args, **kwargs: JSON

    # Also patch the json submodule
    if hasattr(pg_json, 'JSONB'):
        pg_json.JSONB = JSON

    postgresql._patched_for_sqlite = True
