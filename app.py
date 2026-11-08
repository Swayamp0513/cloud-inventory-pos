import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "omnicloud-secure-cloud-key-2026")
DB_PATH = os.environ.get("DB_PATH", "cloud_inventory.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Stores table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            location TEXT,
            manager TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Users table: Roles = 'ADMIN' (Brand Owner) or 'MANAGER' (Franchise Store Manager)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('ADMIN', 'MANAGER')),
            store_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')

    # Inventory items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            item_code TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL,
            reorder_level INTEGER DEFAULT 10,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id),
            UNIQUE(store_id, item_code)
        )
    ''')

    # Bills table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_number TEXT UNIQUE NOT NULL,
            store_id INTEGER NOT NULL,
            created_by_user TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            total_amount REAL NOT NULL,
            payment_mode TEXT DEFAULT 'UPI',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores (id)
        )
    ''')

    # Bill items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (bill_id) REFERENCES bills (id)
        )
    ''')

    # Seed initial franchise stores if empty
    cursor.execute('SELECT COUNT(*) as cnt FROM stores')
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute("INSERT INTO stores (name, code, location, manager) VALUES ('Central Flagship Hub', 'HUB-001', 'City Center HQ', 'Admin Owner')")
        cursor.execute("INSERT INTO stores (name, code, location, manager) VALUES ('Metro Station Express', 'STR-002', 'Terminal 2 Concourse', 'Sneha Rao')")
        cursor.execute("INSERT INTO stores (name, code, location, manager) VALUES ('Suburban Galleria Outlet', 'STR-003', 'Sector 14 Mall', 'Amit Deshmukh')")

    # Seed Default Users if empty
    cursor.execute('SELECT COUNT(*) as cnt FROM users')
    if cursor.fetchone()['cnt'] == 0:
        # Default Brand Owner Admin: owner / admin123
        owner_hash = generate_password_hash("admin123")
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role, store_id)
            VALUES (?, ?, ?, ?, NULL)
        ''', ('owner', owner_hash, 'Global Brand Owner', 'ADMIN'))

        # Default Franchise Managers: manager1 / pass123 (tied to Store 2), manager2 / pass123 (tied to Store 3)
        mgr_hash = generate_password_hash("pass123")
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role, store_id)
            VALUES (?, ?, ?, ?, ?)
        ''', ('manager1', mgr_hash, 'Sneha Rao (Metro Manager)', 'MANAGER', 2))

        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role, store_id)
            VALUES (?, ?, ?, ?, ?)
        ''', ('manager2', mgr_hash, 'Amit Deshmukh (Galleria Manager)', 'MANAGER', 3))

        # Sample initial inventory
        items = [
            (1, 'SKU-001', 'Wireless Barcode Scanner', 'Electronics', 45, 2499.0, 10),
            (1, 'SKU-002', 'Thermal Billing Rolls (Pack of 10)', 'Supplies', 120, 450.0, 25),
            (1, 'SKU-003', 'Ergonomic Desk Organizer', 'General', 15, 899.0, 5),
            (2, 'SKU-001', 'Wireless Barcode Scanner', 'Electronics', 12, 2499.0, 5),
            (2, 'SKU-002', 'Thermal Billing Rolls (Pack of 10)', 'Supplies', 35, 450.0, 15),
            (3, 'SKU-003', 'Ergonomic Desk Organizer', 'General', 40, 899.0, 10),
        ]
        for it in items:
            cursor.execute('''
                INSERT INTO inventory (store_id, item_code, item_name, category, quantity, unit_price, reorder_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', it)

        # Seed initial bills
        cursor.execute("INSERT INTO bills (bill_number, store_id, created_by_user, customer_name, customer_phone, total_amount, payment_mode, created_at) VALUES ('INV-2026-1001', 1, 'owner', 'Rahul Verma', '9876543210', 2949.0, 'UPI', datetime('now', '-2 days'))")
        b1 = cursor.lastrowid
        cursor.execute("INSERT INTO bill_items (bill_id, item_name, quantity, unit_price, total_price) VALUES (?, 'Wireless Barcode Scanner', 1, 2499.0, 2499.0)", (b1,))
        cursor.execute("INSERT INTO bill_items (bill_id, item_name, quantity, unit_price, total_price) VALUES (?, 'Thermal Billing Rolls (Pack of 10)', 1, 450.0, 450.0)", (b1,))

        cursor.execute("INSERT INTO bills (bill_number, store_id, created_by_user, customer_name, customer_phone, total_amount, payment_mode, created_at) VALUES ('INV-2026-1002', 2, 'manager1', 'Pooja Nair', '9123456780', 4998.0, 'Card', datetime('now', '-1 days'))")
        b2 = cursor.lastrowid
        cursor.execute("INSERT INTO bill_items (bill_id, item_name, quantity, unit_price, total_price) VALUES (?, 'Wireless Barcode Scanner', 2, 2499.0, 4998.0)", (b2,))

    conn.commit()
    conn.close()

init_db()

# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Unauthorized. Please sign in.'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

# --- AUTH APIS ---
@app.route('/api/auth/session')
def check_session():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'full_name': session.get('full_name'),
                'role': session.get('role'),
                'store_id': session.get('store_id'),
                'store_name': session.get('store_name')
            }
        })
    return jsonify({'logged_in': False})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'MANAGER').upper() # 'ADMIN' or 'MANAGER'
    store_id = data.get('store_id')

    if not username or not password or not full_name:
        return jsonify({'success': False, 'message': 'All required fields must be filled'}), 400

    if role == 'MANAGER' and not store_id:
        return jsonify({'success': False, 'message': 'A franchise store must be assigned for a Store Manager'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        pw_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role, store_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, pw_hash, full_name, role, store_id if role == 'MANAGER' else None))
        conn.commit()
        return jsonify({'success': True, 'message': 'Registration successful! You can now sign in.'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': f"Username '{username}' is already taken"}), 400
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.*, s.name as store_name
        FROM users u
        LEFT JOIN stores s ON u.store_id = s.id
        WHERE u.username = ?
    ''', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['role'] = user['role']
        session['store_id'] = user['store_id']
        session['store_name'] = user['store_name'] or 'Central Headquarters'
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role': user['role'],
                'store_id': user['store_id'],
                'store_name': user['store_name'] or 'Central Headquarters'
            }
        })
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# --- STORE APIS ---
@app.route('/api/stores', methods=['GET', 'POST'])
def handle_stores():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        if session.get('role') != 'ADMIN':
            conn.close()
            return jsonify({'success': False, 'message': 'Only Brand Owner (ADMIN) can register new franchise stores'}), 403
        data = request.json
        try:
            cursor.execute(
                'INSERT INTO stores (name, code, location, manager) VALUES (?, ?, ?, ?)',
                (data['name'], data['code'].upper(), data.get('location', ''), data.get('manager', ''))
            )
            conn.commit()
            return jsonify({'success': True, 'id': cursor.lastrowid}), 201
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Store code already exists'}), 400
        finally:
            conn.close()

    # GET stores: Admins see all stores; Managers see their assigned store (or all for selection during signup)
    cursor.execute('''
        SELECT s.*, 
               COUNT(DISTINCT i.id) as total_items, 
               COALESCE(SUM(i.quantity), 0) as total_stock,
               COALESCE((SELECT SUM(b.total_amount) FROM bills b WHERE b.store_id = s.id), 0) as total_revenue
        FROM stores s
        LEFT JOIN inventory i ON s.id = i.store_id
        GROUP BY s.id
        ORDER BY s.id ASC
    ''')
    stores = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(stores)

# --- INVENTORY APIS ---
@app.route('/api/inventory', methods=['GET', 'POST'])
def handle_inventory():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        if 'user_id' not in session:
            conn.close()
            return jsonify({'success': False, 'message': 'Login required'}), 401

        data = request.json
        store_id = int(data['store_id'])

        # Role enforcement: Franchise manager cannot edit stock of another franchise!
        if session.get('role') == 'MANAGER' and session.get('store_id') != store_id:
            conn.close()
            return jsonify({'success': False, 'message': 'Access Denied: You can only manage inventory for your assigned branch.'}), 403

        code = data['item_code'].strip().upper()
        name = data['item_name'].strip()
        cat = data.get('category', 'General')
        qty = int(data.get('quantity', 0))
        price = float(data.get('unit_price', 0.0))
        reorder = int(data.get('reorder_level', 10))

        cursor.execute('''
            INSERT INTO inventory (store_id, item_code, item_name, category, quantity, unit_price, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(store_id, item_code) DO UPDATE SET
                item_name = excluded.item_name,
                category = excluded.category,
                quantity = excluded.quantity,
                unit_price = excluded.unit_price,
                reorder_level = excluded.reorder_level,
                updated_at = CURRENT_TIMESTAMP
        ''', (store_id, code, name, cat, qty, price, reorder))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Inventory updated successfully'})

    store_id = request.args.get('store_id')
    query = '''
        SELECT i.*, s.name as store_name, s.code as store_code
        FROM inventory i
        JOIN stores s ON i.store_id = s.id
    '''
    params = []

    # If manager is logged in and requests inventory, isolate to their store if requested or default
    if session.get('role') == 'MANAGER':
        query += ' WHERE i.store_id = ?'
        params.append(session.get('store_id'))
    elif store_id and store_id != 'all':
        query += ' WHERE i.store_id = ?'
        params.append(store_id)

    query += ' ORDER BY i.item_name ASC'
    cursor.execute(query, params)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(items)

# --- BILLING & POS ---
@app.route('/api/bills', methods=['GET', 'POST'])
def handle_bills():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        if 'user_id' not in session:
            conn.close()
            return jsonify({'success': False, 'message': 'Login required to generate bills'}), 401

        data = request.json
        store_id = int(data['store_id'])

        # Managers can only bill from their own branch
        if session.get('role') == 'MANAGER' and session.get('store_id') != store_id:
            conn.close()
            return jsonify({'success': False, 'message': 'Unauthorized: Cannot create bills for other outlets'}), 403

        customer_name = data.get('customer_name', 'Walk-in Customer')
        customer_phone = data.get('customer_phone', '')
        payment_mode = data.get('payment_mode', 'UPI')
        cart = data.get('items', [])

        if not cart:
            conn.close()
            return jsonify({'success': False, 'message': 'Cart cannot be empty'}), 400

        total_amount = sum(float(item['unit_price']) * int(item['quantity']) for item in cart)
        bill_num = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{store_id}"

        try:
            for it in cart:
                cursor.execute('SELECT quantity FROM inventory WHERE store_id = ? AND item_code = ?', (store_id, it['item_code']))
                stock_row = cursor.fetchone()
                if not stock_row or stock_row['quantity'] < it['quantity']:
                    return jsonify({'success': False, 'message': f"Insufficient stock for {it['item_name']}"}), 400

            cursor.execute('''
                INSERT INTO bills (bill_number, store_id, created_by_user, customer_name, customer_phone, total_amount, payment_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (bill_num, store_id, session.get('username'), customer_name, customer_phone, total_amount, payment_mode))
            bill_id = cursor.lastrowid

            for it in cart:
                qty = int(it['quantity'])
                u_price = float(it['unit_price'])
                t_price = qty * u_price
                cursor.execute('''
                    INSERT INTO bill_items (bill_id, item_name, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (bill_id, it['item_name'], qty, u_price, t_price))

                cursor.execute('''
                    UPDATE inventory 
                    SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE store_id = ? AND item_code = ?
                ''', (qty, store_id, it['item_code']))

            conn.commit()
            return jsonify({'success': True, 'bill_number': bill_num, 'total_amount': total_amount, 'bill_id': bill_id})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()

    # GET bills
    query = '''
        SELECT b.*, s.name as store_name, s.code as store_code
        FROM bills b
        JOIN stores s ON b.store_id = s.id
    '''
    params = []
    if session.get('role') == 'MANAGER':
        query += ' WHERE b.store_id = ?'
        params.append(session.get('store_id'))
    elif request.args.get('store_id') and request.args.get('store_id') != 'all':
        query += ' WHERE b.store_id = ?'
        params.append(request.args.get('store_id'))

    query += ' ORDER BY b.created_at DESC LIMIT 50'
    cursor.execute(query, params)
    bills = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(bills)

# --- BUSINESS ANALYTICS & REPORTS ---
@app.route('/api/reports')
def get_reports():
    conn = get_db()
    cursor = conn.cursor()

    is_manager = session.get('role') == 'MANAGER'
    mgr_store = session.get('store_id')

    if is_manager:
        cursor.execute('SELECT COUNT(*) as store_count FROM stores WHERE id = ?', (mgr_store,))
        store_count = cursor.fetchone()['store_count']

        cursor.execute('SELECT COALESCE(SUM(quantity), 0) as total_units, COUNT(*) as total_skus FROM inventory WHERE store_id = ?', (mgr_store,))
        inv_stat = cursor.fetchone()

        cursor.execute('SELECT COALESCE(SUM(total_amount), 0) as total_sales, COUNT(*) as bill_count FROM bills WHERE store_id = ?', (mgr_store,))
        sales_stat = cursor.fetchone()

        cursor.execute('''
            SELECT s.name as store_name, s.code, COALESCE(SUM(b.total_amount), 0) as revenue, COUNT(b.id) as orders
            FROM stores s
            LEFT JOIN bills b ON s.id = b.store_id
            WHERE s.id = ?
            GROUP BY s.id
        ''', (mgr_store,))
        store_sales = [dict(r) for r in cursor.fetchall()]

        cursor.execute('''
            SELECT i.item_name, i.item_code, i.quantity, i.reorder_level, s.name as store_name
            FROM inventory i
            JOIN stores s ON i.store_id = s.id
            WHERE i.store_id = ? AND i.quantity <= i.reorder_level
            ORDER BY i.quantity ASC
        ''', (mgr_store,))
        low_stocks = [dict(r) for r in cursor.fetchall()]

        cursor.execute('''
            SELECT bi.item_name, SUM(bi.quantity) as sold_qty, SUM(bi.total_price) as total_rev
            FROM bill_items bi
            JOIN bills b ON bi.bill_id = b.id
            WHERE b.store_id = ?
            GROUP BY bi.item_name
            ORDER BY sold_qty DESC
            LIMIT 5
        ''', (mgr_store,))
        top_items = [dict(r) for r in cursor.fetchall()]
    else:
        # Brand Owner Global View
        cursor.execute('SELECT COUNT(*) as store_count FROM stores')
        store_count = cursor.fetchone()['store_count']

        cursor.execute('SELECT COALESCE(SUM(quantity), 0) as total_units, COUNT(*) as total_skus FROM inventory')
        inv_stat = cursor.fetchone()

        cursor.execute('SELECT COALESCE(SUM(total_amount), 0) as total_sales, COUNT(*) as bill_count FROM bills')
        sales_stat = cursor.fetchone()

        cursor.execute('''
            SELECT s.name as store_name, s.code, COALESCE(SUM(b.total_amount), 0) as revenue, COUNT(b.id) as orders
            FROM stores s
            LEFT JOIN bills b ON s.id = b.store_id
            GROUP BY s.id
            ORDER BY revenue DESC
        ''')
        store_sales = [dict(r) for r in cursor.fetchall()]

        cursor.execute('''
            SELECT i.item_name, i.item_code, i.quantity, i.reorder_level, s.name as store_name
            FROM inventory i
            JOIN stores s ON i.store_id = s.id
            WHERE i.quantity <= i.reorder_level
            ORDER BY i.quantity ASC
        ''')
        low_stocks = [dict(r) for r in cursor.fetchall()]

        cursor.execute('''
            SELECT bi.item_name, SUM(bi.quantity) as sold_qty, SUM(bi.total_price) as total_rev
            FROM bill_items bi
            GROUP BY bi.item_name
            ORDER BY sold_qty DESC
            LIMIT 5
        ''')
        top_items = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        'summary': {
            'total_stores': store_count,
            'total_stock_units': inv_stat['total_units'],
            'total_skus': inv_stat['total_skus'],
            'total_revenue': sales_stat['total_sales'],
            'total_bills': sales_stat['bill_count']
        },
        'store_performance': store_sales,
        'low_stock_alerts': low_stocks,
        'top_selling_products': top_items
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
