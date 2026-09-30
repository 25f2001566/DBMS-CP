import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import mysql.connector
from mysql.connector import Error
from backend.config import Config

def get_db_connection():
    """Establish and return a connection to MySQL database."""
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            autocommit=True
        )
        return conn
    except Error as e:
        # Also try without database specified in case database hasn't been initialized yet
        try:
            conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                autocommit=True
            )
            return conn
        except Error:
            raise e

def execute_query(query, params=None, fetch_all=True):
    """Execute SELECT query and return rows as dictionary list."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.fetchone()
        return result
    finally:
        cursor.close()
        conn.close()

def execute_dml(query, params=None):
    """Execute INSERT/UPDATE/DELETE query and return affected rows and last_insert_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        conn.commit()
        last_id = cursor.lastrowid
        row_count = cursor.rowcount
        return {"affected_rows": row_count, "last_id": last_id}
    finally:
        cursor.close()
        conn.close()

def call_procedure(proc_name, params=()):
    """Call a MySQL stored procedure and return output parameters/datasets."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.callproc(proc_name, params)
        results = []
        for result in cursor.stored_results():
            results.extend(result.fetchall())
        conn.commit()
        return results
    finally:
        cursor.close()
        conn.close()
