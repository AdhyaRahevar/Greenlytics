import sqlite3
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'database.db')

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            name TEXT,
            image_url TEXT,
            tags TEXT,
            eco_score INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            price REAL,
            date TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_products (
            user_id INTEGER,
            product_id INTEGER,
            target_price REAL DEFAULT 0.0,
            PRIMARY KEY (user_id, product_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            message TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # Check for category column migration
    c.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in c.fetchall()]
    if 'category' not in columns:
        c.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'Others'")

    conn.commit()
    conn.close()

# Users
def register_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    try:
        pw_hash = generate_password_hash(password)
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pw_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[1], password):
        return user[0]
    return None

# Products
def get_product_by_url(url):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM products WHERE url = ?', (url,))
    rv = c.fetchone()
    conn.close()
    return rv[0] if rv else None

def add_product(url, name, image_url='', tags='', eco_score=0, category='Others'):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO products (url, name, image_url, tags, eco_score, category) VALUES (?, ?, ?, ?, ?, ?)', 
              (url, name, image_url, tags, eco_score, category))
    conn.commit()
    c.execute('SELECT id FROM products WHERE url = ?', (url,))
    product_id = c.fetchone()[0]
    if name and name != "Unknown Product":
        c.execute('UPDATE products SET name = ?, image_url = ?, tags = ?, eco_score = ?, category = ? WHERE id = ?', 
                  (name, image_url, tags, eco_score, category, product_id))
        conn.commit()
    conn.close()
    return product_id

def add_user_product(user_id, product_id, target_price=0.0):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO user_products (user_id, product_id, target_price) VALUES (?, ?, ?)',
              (user_id, product_id, target_price))
    conn.commit()
    conn.close()

def set_target_price(user_id, product_id, target_price):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE user_products SET target_price = ? WHERE user_id = ? AND product_id = ?', 
              (target_price, user_id, product_id))
    conn.commit()
    conn.close()

def remove_user_product(user_id, product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM user_products WHERE user_id = ? AND product_id = ?', (user_id, product_id))
    conn.commit()
    conn.close()

# Fetching Data
def get_user_products(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT p.id, p.url, p.name, p.image_url, p.tags, p.eco_score, p.category, up.target_price
        FROM products p
        JOIN user_products up ON p.id = up.product_id
        WHERE up.user_id = ?
    ''', (user_id,))
    products = [dict(row) for row in c.fetchall()]
    conn.close()
    return products

def get_all_products():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, url, name, category, image_url, tags, eco_score FROM products')
    products = [dict(row) for row in c.fetchall()]
    conn.close()
    return products

def get_category_stats(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT p.category, COUNT(p.id) 
        FROM products p
        JOIN user_products up ON p.id = up.product_id
        WHERE up.user_id = ? AND p.category IS NOT NULL
        GROUP BY p.category
    ''', (user_id,))
    data = dict(c.fetchall())
    conn.close()
    return data

def count_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    rv = c.fetchone()
    conn.close()
    return rv[0] if rv else 0

# Pricing
def add_price(product_id, price):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO prices (product_id, price, date) VALUES (?, ?, ?)', 
              (product_id, price, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_price_history(product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT price, date FROM prices WHERE product_id = ? ORDER BY date', (product_id,))
    history = [{'price': row[0], 'date': row[1][:10]} for row in c.fetchall()]
    conn.close()
    return history

def get_latest_price(product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT price, date FROM prices WHERE product_id = ? ORDER BY date DESC LIMIT 1', (product_id,))
    row = c.fetchone()
    conn.close()
    return {'price': row[0], 'date': row[1][:10]} if row else None

def get_average_price(product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT AVG(price) FROM prices WHERE product_id = ?', (product_id,))
    row = c.fetchone()
    conn.close()
    return round(row[0], 2) if row[0] else 0.0

# Alert Check Helper
def get_interested_users(product_id, price):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.username, up.target_price 
        FROM user_products up JOIN users u ON u.id = up.user_id 
        WHERE up.product_id = ? AND up.target_price >= ? AND up.target_price > 0
    ''', (product_id, price))
    users = c.fetchall()
    conn.close()
    return users

# Notifications
def add_notification(user_id, product_id, message):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO notifications (user_id, product_id, message, created_at) VALUES (?, ?, ?, ?)',
              (user_id, product_id, message, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_unread_notifications(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT n.*, p.name as product_name FROM notifications n LEFT JOIN products p ON p.id = n.product_id WHERE n.user_id = ? AND n.is_read = 0 ORDER BY n.created_at DESC', (user_id,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def mark_notifications_read(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0', (user_id,))
    conn.commit()
    conn.close()
