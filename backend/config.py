import os

class Config:
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '@devrajmysql123')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'ecommerce_db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-multivendor-ecommerce-secret-key-2026')
