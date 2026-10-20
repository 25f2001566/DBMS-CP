"""
Authentication + role-based access control (RBAC).

How it works (viva summary)
---------------------------
1. Passwords are stored only as salted hashes (Werkzeug PBKDF2-SHA256), never as text.
2. After a correct login the server puts the user's id into Flask's *signed* session cookie.
   The browser cannot change it without invalidating the signature (SECRET_KEY).
3. Every protected route is wrapped in @role_required(...). On EVERY request the server
   re-reads the user from MySQL, so deactivating an account or a vendor takes effect at once,
   and the role always comes from the database - never from the browser.
4. Each login page ("portal") only accepts accounts of its own role.
"""
import re
from functools import wraps

import mysql.connector
from flask import Blueprint, g, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.db import execute_dml, execute_query, get_db_connection

auth_bp = Blueprint('auth', __name__)

HASH_METHOD = 'pbkdf2:sha256'
DASHBOARD_URL = {'admin': '/admin', 'vendor': '/vendor', 'customer': '/customer'}
LOGIN_URL = {'admin': '/admin/login', 'vendor': '/vendor/login', 'customer': '/login'}
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Used so a wrong e-mail takes as long to reject as a wrong password (no user enumeration by timing).
_DUMMY_HASH = generate_password_hash('not-a-real-password', method=HASH_METHOD)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def hash_password(plain):
    return generate_password_hash(plain, method=HASH_METHOD)


def _account_problem(row):
    """Return a message if this account may not log in / keep a session, else None."""
    if not row['is_active']:
        return 'This account has been deactivated. Please contact the administrator.'
    if row['role'] == 'customer' and row['cust_status'] != 'Active':
        return 'This account has been deactivated. Please contact the administrator.'
    if row['role'] == 'vendor':
        if row['seller_status'] == 'Pending':
            return 'Your vendor account is waiting for admin approval.'
        if row['seller_status'] != 'Active':
            return 'This vendor account has been deactivated. Please contact the administrator.'
    return None


_USER_SQL = """
    SELECT u.user_id, u.email, u.password_hash, u.role, u.customer_id, u.seller_id, u.is_active,
           c.status AS cust_status, CONCAT(c.first_name, ' ', c.last_name) AS cust_name,
           s.status AS seller_status, s.seller_name
    FROM App_User u
    LEFT JOIN Customer c ON c.customer_id = u.customer_id
    LEFT JOIN Seller   s ON s.seller_id   = u.seller_id
"""


def _display_name(row):
    if row['role'] == 'customer':
        return row['cust_name']
    if row['role'] == 'vendor':
        return row['seller_name']
    return 'Administrator'


def current_user():
    """The logged-in user, freshly validated against the database (cached per request)."""
    if 'user' in g:
        return g.user
    g.user = None
    user_id = session.get('user_id')
    if user_id:
        row = execute_query(_USER_SQL + ' WHERE u.user_id = %s', (user_id,), fetch_all=False)
        if row and _account_problem(row) is None:
            g.user = {
                'user_id': row['user_id'], 'email': row['email'], 'role': row['role'],
                'customer_id': row['customer_id'], 'seller_id': row['seller_id'],
                'name': _display_name(row),
            }
        else:
            session.clear()
    return g.user


def role_required(*roles):
    """Decorator: only logged-in users whose role is in `roles` may call this route."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            is_api = request.path.startswith('/api/')
            if user is None:
                if is_api:
                    return jsonify({'status': 'error', 'message': 'Please log in first.'}), 401
                return redirect(LOGIN_URL[roles[0]])
            if user['role'] not in roles:
                if is_api:
                    return jsonify({'status': 'error', 'message': 'You do not have permission to do this.'}), 403
                return redirect(DASHBOARD_URL[user['role']])   # send them to their OWN area
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ------------------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------------------
def _portal_page(portal, mode='login'):
    user = current_user()
    if user:
        return redirect(DASHBOARD_URL[user['role']])
    return render_template('login.html', portal=portal, mode=mode)


@auth_bp.route('/login')
def customer_login_page():
    return _portal_page('customer')


@auth_bp.route('/register')
def customer_register_page():
    return _portal_page('customer', 'register')


@auth_bp.route('/vendor/login')
def vendor_login_page():
    return _portal_page('vendor')


@auth_bp.route('/vendor/register')
def vendor_register_page():
    return _portal_page('vendor', 'register')


@auth_bp.route('/admin/login')
def admin_login_page():
    return _portal_page('admin')


# ------------------------------------------------------------------------------
# API
# ------------------------------------------------------------------------------
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    portal = data.get('portal')

    row = execute_query(_USER_SQL + ' WHERE u.email = %s', (email,), fetch_all=False) if email else None
    stored_hash = row['password_hash'] if row else _DUMMY_HASH
    password_ok = check_password_hash(stored_hash, password)

    if not row or not password_ok:
        return jsonify({'status': 'error', 'message': 'Invalid email or password.'}), 401

    if portal in LOGIN_URL and row['role'] != portal:
        return jsonify({'status': 'error',
                        'message': f"This is the {portal} login. Your account is a {row['role']} account - "
                                   f"please use the {row['role']} login page."}), 403

    problem = _account_problem(row)
    if problem:
        return jsonify({'status': 'error', 'message': problem}), 403

    session.clear()
    session['user_id'] = row['user_id']
    execute_dml('UPDATE App_User SET last_login = NOW() WHERE user_id = %s', (row['user_id'],))
    return jsonify({'status': 'success', 'redirect': DASHBOARD_URL[row['role']]})


@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'status': 'success'})


@auth_bp.route('/api/auth/me')
def api_me():
    user = current_user()
    if not user:
        return jsonify({'status': 'error', 'message': 'Not logged in.'}), 401
    return jsonify({'status': 'success', 'user': {'name': user['name'], 'role': user['role'], 'email': user['email']}})


def _validate_common(data):
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    if not EMAIL_RE.match(email) or len(email) > 100:
        return None, None, 'Please enter a valid email address.'
    if len(password) < 8:
        return None, None, 'Password must be at least 8 characters.'
    return email, password, None


def _register(insert_profile, data):
    """Run profile insert + App_User insert in ONE transaction so we never keep half an account."""
    email, password, error = _validate_common(data)
    if error:
        return jsonify({'status': 'error', 'message': error}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        conn.start_transaction()
        insert_profile(cur, email, password)
        conn.commit()
        return jsonify({'status': 'success'})
    except mysql.connector.IntegrityError:
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'An account with this email or phone number already exists.'}), 409
    except ValueError as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception:
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'Could not create the account. Please try again.'}), 500
    finally:
        cur.close()
        conn.close()


@auth_bp.route('/api/auth/register/customer', methods=['POST'])
def register_customer():
    data = request.get_json(silent=True) or {}
    first = str(data.get('first_name', '')).strip()
    last = str(data.get('last_name', '')).strip()
    city = str(data.get('city', '')).strip()
    phone = str(data.get('phone', '')).strip() or None   # '' would clash with the UNIQUE phone column

    def insert_profile(cur, email, password):
        if not first or not last or not city:
            raise ValueError('First name, last name and city are required.')
        cur.execute("""INSERT INTO Customer (first_name, last_name, email, phone, registration_date, city)
                       VALUES (%s, %s, %s, %s, CURDATE(), %s)""", (first, last, email, phone, city))
        customer_id = cur.lastrowid
        cur.execute('INSERT INTO Cart (customer_id, created_date) VALUES (%s, CURDATE())', (customer_id,))
        cur.execute("""INSERT INTO App_User (email, password_hash, role, customer_id)
                       VALUES (%s, %s, 'customer', %s)""", (email, hash_password(password), customer_id))

    return _register(insert_profile, data)


@auth_bp.route('/api/auth/register/vendor', methods=['POST'])
def register_vendor():
    data = request.get_json(silent=True) or {}
    store = str(data.get('store_name', '')).strip()
    city = str(data.get('city', '')).strip()
    phone = str(data.get('phone', '')).strip() or None

    def insert_profile(cur, email, password):
        if not store or not city:
            raise ValueError('Store name and city are required.')
        # New vendors start as 'Pending'; an admin must approve them before they can log in.
        cur.execute("""INSERT INTO Seller (seller_name, email, phone, city, registration_date, status)
                       VALUES (%s, %s, %s, %s, CURDATE(), 'Pending')""", (store, email, phone, city))
        seller_id = cur.lastrowid
        cur.execute("""INSERT INTO App_User (email, password_hash, role, seller_id)
                       VALUES (%s, %s, 'vendor', %s)""", (email, hash_password(password), seller_id))

    return _register(insert_profile, data)
