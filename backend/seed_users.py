"""
Creates demo logins for the sample data already in the database.

Run from the project root (after `python -m backend.init_db`):
    python -m backend.seed_users

DEMO PASSWORDS ONLY - fine for a classroom demo, never for a real site.
Safe to run again: it only adds logins that do not exist yet.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.auth import hash_password
from backend.db import get_db_connection

ADMIN_EMAIL = 'admin@smartstore.com'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@123')
VENDOR_PASSWORD = 'Vendor@123'
CUSTOMER_PASSWORD = 'Customer@123'


def seed():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM App_User WHERE role = %s', ('admin',))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO App_User (email, password_hash, role) VALUES (%s, %s, 'admin')",
                        (ADMIN_EMAIL, hash_password(ADMIN_PASSWORD)))
            print(f'Admin created:     {ADMIN_EMAIL}  /  {ADMIN_PASSWORD}')

        # Hash once per role: same demo password, but each row still gets its own salt when hashed.
        cur.execute("""SELECT s.seller_id, s.email FROM Seller s
                       LEFT JOIN App_User u ON u.seller_id = s.seller_id WHERE u.user_id IS NULL""")
        vendors = cur.fetchall()
        for seller_id, email in vendors:
            cur.execute("INSERT INTO App_User (email, password_hash, role, seller_id) VALUES (%s, %s, 'vendor', %s)",
                        (email.lower(), hash_password(VENDOR_PASSWORD), seller_id))
        print(f'Vendor logins added:   {len(vendors)}  (password: {VENDOR_PASSWORD})')

        cur.execute("""SELECT c.customer_id, c.email FROM Customer c
                       LEFT JOIN App_User u ON u.customer_id = c.customer_id WHERE u.user_id IS NULL""")
        customers = cur.fetchall()
        for customer_id, email in customers:
            cur.execute("INSERT INTO App_User (email, password_hash, role, customer_id) VALUES (%s, %s, 'customer', %s)",
                        (email.lower(), hash_password(CUSTOMER_PASSWORD), customer_id))
        print(f'Customer logins added: {len(customers)}  (password: {CUSTOMER_PASSWORD})')
        conn.commit()
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    seed()
