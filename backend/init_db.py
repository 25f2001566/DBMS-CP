import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import re
import mysql.connector
from backend.config import Config

def run_sql_file(cursor, filepath):
    print(f"Executing: {os.path.basename(filepath)}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Handle DELIMITER blocks (procedures, functions, triggers)
    if 'DELIMITER //' in sql:
        # Split by DELIMITER // and DELIMITER ;
        parts = re.split(r'DELIMITER\s+//', sql)
        # Execute initial part
        initial_statements = parts[0].split(';')
        for stmt in initial_statements:
            clean = stmt.strip()
            if clean and not clean.startswith('--'):
                cursor.execute(clean)

        for block in parts[1:]:
            sub_parts = re.split(r'DELIMITER\s+;', block)
            # The code inside DELIMITER // is separated by //
            proc_block = sub_parts[0]
            routines = proc_block.split('//')
            for r in routines:
                clean = r.strip()
                if clean:
                    cursor.execute(clean)
            
            # Any remaining statements after DELIMITER ;
            if len(sub_parts) > 1:
                after_stmts = sub_parts[1].split(';')
                for stmt in after_stmts:
                    clean = stmt.strip()
                    if clean and not clean.startswith('--'):
                        cursor.execute(clean)
    else:
        # Standard statement-by-statement execution
        statements = sql.split(';')
        for statement in statements:
            clean_stmt = statement.strip()
            if clean_stmt and not clean_stmt.startswith('--'):
                try:
                    cursor.execute(clean_stmt)
                except Exception as e:
                    print(f"Warning on statement: {clean_stmt[:50]}... -> {e}")

def initialize_database(password=None):
    if password is not None:
        Config.MYSQL_PASSWORD = password

    print(f"Connecting to MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT} as {Config.MYSQL_USER}...")
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        autocommit=True
    )
    cursor = conn.cursor()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, 'database')
    
    files = [
        '01_schema_ddl.sql',
        '02_sample_dml.sql',
        '06_cursors.sql',
        '07_procedures.sql',
        '08_functions.sql',
        '09_triggers.sql',
        '10_views_and_indexing.sql'
    ]

    for filename in files:
        filepath = os.path.join(db_dir, filename)
        if os.path.exists(filepath):
            run_sql_file(cursor, filepath)

    cursor.close()
    conn.close()
    print("All database scripts executed successfully!")

if __name__ == '__main__':
    initialize_database()
