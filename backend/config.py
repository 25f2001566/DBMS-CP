"""
Configuration. Secrets are NOT stored in code any more.
Put them in a file named `.env` in the project root (see `.env.example`),
or set them as normal environment variables.
"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv(path):
    """Tiny .env reader (KEY=value per line) so we need no extra library."""
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'ecommerce_db')

    # If no SECRET_KEY is configured, use a random one (everyone is logged out on restart).
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    SESSION_COOKIE_HTTPONLY = True      # JavaScript cannot read the session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'     # cookie not sent on cross-site POSTs (basic CSRF protection)
