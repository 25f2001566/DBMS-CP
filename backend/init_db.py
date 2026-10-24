"""
Database setup runner.

Run from the project root:   python -m backend.init_db

It executes the SQL scripts in /database in order against MySQL.
The splitter below understands `DELIMITER` lines (needed for procedures,
functions and triggers) and ignores full-line `--` comments, so every
statement in every script is really executed.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import mysql.connector
from backend.config import Config

# Order matters: later scripts depend on earlier ones.
SCRIPTS = [
    '01_schema_ddl.sql',
    '02_sample_dml.sql',
    '06_cursors.sql',
    '07_procedures.sql',
    '08_functions.sql',
    '09_triggers.sql',
    '10_views_and_indexing.sql',
    '11_roles_and_multivendor.sql',
]


def split_sql(text):
    """Split a SQL script into single statements, honouring DELIMITER changes."""
    delimiter = ';'
    statements, buffer = [], []
    for line in text.splitlines():
        stripped = line.strip()

        if not buffer and (not stripped or stripped.startswith('--')):
            continue  # blank line or full-line comment between statements

        if not buffer and stripped.upper().startswith('DELIMITER'):
            delimiter = stripped.split(None, 1)[1].strip()
            continue

        buffer.append(line)
        if stripped.endswith(delimiter):
            stmt = '\n'.join(buffer).strip()
            stmt = stmt[: -len(delimiter)].strip()
            if stmt:
                statements.append(stmt)
            buffer = []

    leftover = '\n'.join(buffer).strip()
    if leftover:
        statements.append(leftover)
    return statements


def run_sql_file(cursor, filepath):
    print(f"Executing: {os.path.basename(filepath)} ...")

    with open(filepath, 'r', encoding='utf-8') as f:
        statements = split_sql(f.read())

    for stmt in statements:
        cursor.execute(stmt)

        # Consume all rows and any additional result sets.
        while True:
            if cursor.with_rows:
                cursor.fetchall()

            if not cursor.nextset():
                break

    print(f"   {len(statements)} statements OK")


def initialize_database():
    print(f"Connecting to MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT} as {Config.MYSQL_USER} ...")
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        autocommit=True,
    )
    cursor = conn.cursor()
    db_dir = os.path.join(BASE_DIR, 'database')

    for filename in SCRIPTS:
        filepath = os.path.join(db_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Missing SQL script: {filepath}")
        run_sql_file(cursor, filepath)

    cursor.close()
    conn.close()
    print("Database ready.")


if __name__ == '__main__':
    initialize_database()
