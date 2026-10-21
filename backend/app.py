import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, jsonify, request, render_template, redirect, send_from_directory
from backend.config import Config
from backend.db import execute_query, execute_dml, call_procedure, get_db_connection
from backend.auth import auth_bp, role_required, current_user, LOGIN_URL, DASHBOARD_URL

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'static')
)
app.config.from_object(Config)
app.register_blueprint(auth_bp)

# ------------------------------------------------------------------------------
# FRONTEND ROUTES
# ------------------------------------------------------------------------------
@app.route('/')
def index():
    user = current_user()
    return redirect(DASHBOARD_URL[user['role']] if user else '/login')

@app.route('/admin')
@role_required('admin')
def admin_dashboard():
    return render_template('index.html')

@app.route('/customer')
@role_required('customer')
def customer_home():
    user = current_user()
    return render_template('customer_storefront.html', user=user)

@app.route('/vendor')
@role_required('vendor')
def vendor_home():
    user = current_user()
    return render_template('vendor_dashboard.html', user=user)

# ------------------------------------------------------------------------------
# 1. DASHBOARD & SUMMARY METRICS API
# ------------------------------------------------------------------------------
@app.route('/api/dashboard/stats', methods=['GET'])
@role_required('admin')
def get_dashboard_stats():
    try:
        # Aggregated KPI metrics
        counts = execute_query("""
            SELECT 
                (SELECT COUNT(*) FROM Customer) AS total_customers,
                (SELECT COUNT(*) FROM Seller) AS total_vendors,
                (SELECT COUNT(*) FROM Product) AS total_products,
                (SELECT COUNT(*) FROM Orders) AS total_orders,
                (SELECT COALESCE(SUM(total_amount), 0) FROM Orders WHERE order_status <> 'Cancelled') AS total_revenue,
                (SELECT COUNT(*) FROM Orders WHERE order_status IN ('Pending', 'Processing')) AS pending_orders,
                (SELECT COUNT(*) FROM Product WHERE stock_quantity <= 10) AS low_stock_products
        """, fetch_all=False)

        # Category sales distribution for Chart.js
        cat_dist = execute_query("""
            SELECT 
                c.category_name, 
                COUNT(p.product_id) AS product_count,
                COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS category_revenue
            FROM Category c
            LEFT JOIN Product p ON c.category_id = p.category_id
            LEFT JOIN Order_Item oi ON p.product_id = oi.product_id
            GROUP BY c.category_id, c.category_name
            ORDER BY category_revenue DESC
        """)

        # Recent orders
        recent_orders = execute_query("""
            SELECT 
                o.order_id,
                CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                o.order_date,
                o.total_amount,
                o.order_status,
                p.payment_method,
                p.payment_status
            FROM Orders o
            JOIN Customer c ON o.customer_id = c.customer_id
            LEFT JOIN Payment p ON o.order_id = p.order_id
            ORDER BY o.order_date DESC, o.order_id DESC
            LIMIT 6
        """)

        return jsonify({
            "status": "success",
            "kpis": counts,
            "category_distribution": cat_dist,
            "recent_orders": recent_orders
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------------------------------------------------------------------
# 2. CUSTOMERS API
# ------------------------------------------------------------------------------
@app.route('/api/customers', methods=['GET', 'POST'])
@role_required('admin')
def manage_customers():
    if request.method == 'GET':
        search = request.args.get('search', '').strip()
        if search:
            query = """
                SELECT c.*, COUNT(o.order_id) AS total_orders, COALESCE(SUM(o.total_amount), 0) AS total_spent
                FROM Customer c
                LEFT JOIN Orders o ON c.customer_id = o.customer_id
                WHERE c.first_name LIKE %s OR c.last_name LIKE %s OR c.city LIKE %s OR c.email LIKE %s
                GROUP BY c.customer_id
                ORDER BY c.customer_id DESC
            """
            wildcard = f"%{search}%"
            rows = execute_query(query, (wildcard, wildcard, wildcard, wildcard))
        else:
            query = """
                SELECT c.*, COUNT(o.order_id) AS total_orders, COALESCE(SUM(o.total_amount), 0) AS total_spent
                FROM Customer c
                LEFT JOIN Orders o ON c.customer_id = o.customer_id
                GROUP BY c.customer_id
                ORDER BY c.customer_id DESC
            """
            rows = execute_query(query)
        return jsonify({"status": "success", "data": rows})

    elif request.method == 'POST':
        data = request.json or {}
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip() or None
        city = data.get('city', '').strip()
        status = data.get('status', 'Active')

        if not first_name or not last_name or not email:
            return jsonify({"status": "error", "message": "First name, last name, and email are required."}), 400

        try:
            res = execute_dml("""
                INSERT INTO Customer (first_name, last_name, email, phone, registration_date, city, status)
                VALUES (%s, %s, %s, %s, CURDATE(), %s, %s)
            """, (first_name, last_name, email, phone, city, status))
            return jsonify({"status": "success", "message": "Customer registered successfully.", "customer_id": res["last_id"]})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/customers/<int:cust_id>', methods=['PUT', 'DELETE'])
@role_required('admin')
def customer_detail(cust_id):
    if request.method == 'PUT':
        data = request.json or {}
        try:
            execute_dml("""
                UPDATE Customer 
                SET first_name = %s, last_name = %s, phone = %s, city = %s, status = %s
                WHERE customer_id = %s
            """, (data.get('first_name'), data.get('last_name'), data.get('phone'), data.get('city'), data.get('status', 'Active'), cust_id))
            return jsonify({"status": "success", "message": "Customer updated successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    elif request.method == 'DELETE':
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            cursor = conn.cursor()

            # Confirm that the customer exists.
            cursor.execute(
                "SELECT customer_id FROM Customer WHERE customer_id = %s",
                (cust_id,)
            )
            if cursor.fetchone() is None:
                conn.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Customer not found."
                }), 404

            # Preserve customers who have order history.
            cursor.execute(
                "SELECT COUNT(*) FROM Orders WHERE customer_id = %s",
                (cust_id,)
            )
            order_count = cursor.fetchone()[0]

            if order_count > 0:
                cursor.execute(
                    "UPDATE Customer SET status = 'Inactive' "
                    "WHERE customer_id = %s",
                    (cust_id,)
                )
                cursor.execute(
                    "UPDATE App_User SET is_active = FALSE "
                    "WHERE customer_id = %s",
                    (cust_id,)
                )
                conn.commit()

                return jsonify({
                    "status": "success",
                    "message": (
                        "Customer has order history. "
                        "The account was deactivated and "
                        "the order records were preserved."
                    )
                })

            # No orders exist: remove the linked login first.
            cursor.execute(
                "DELETE FROM App_User WHERE customer_id = %s",
                (cust_id,)
            )

            # Now the customer profile can be deleted.
            cursor.execute(
                "DELETE FROM Customer WHERE customer_id = %s",
                (cust_id,)
            )

            conn.commit()

            return jsonify({
                "status": "success",
                "message": "Customer and linked login deleted successfully."
            })

        except Exception as e:
            if conn:
                conn.rollback()

            return jsonify({
                "status": "error",
                "message": str(e)
            }), 400

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

# ------------------------------------------------------------------------------
# 3. VENDORS / SELLERS API
# ------------------------------------------------------------------------------
@app.route('/api/vendors', methods=['GET', 'POST'])
@role_required('admin')
def manage_vendors():
    if request.method == 'GET':
        vendors = execute_query("""
            SELECT 
                s.*,
                COUNT(DISTINCT p.product_id) AS total_products,
                COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS gross_sales,
                ROUND(COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) * (s.commission_rate / 100), 2) AS commission_earned
            FROM Seller s
            LEFT JOIN Product p ON s.seller_id = p.seller_id
            LEFT JOIN Order_Item oi ON p.product_id = oi.product_id
            LEFT JOIN Orders o ON oi.order_id = o.order_id AND o.order_status <> 'Cancelled'
            GROUP BY s.seller_id
            ORDER BY gross_sales DESC
        """)
        return jsonify({"status": "success", "data": vendors})

    elif request.method == 'POST':
        data = request.json or {}
        try:
            res = execute_dml("""
                INSERT INTO Seller (seller_name, email, phone, city, rating, commission_rate, registration_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), %s)
            """, (
                data.get('seller_name'),
                data.get('email'),
                data.get('phone'),
                data.get('city'),
                float(data.get('rating', 4.0)),
                float(data.get('commission_rate', 10.0)),
                data.get('status', 'Active')
            ))
            return jsonify({"status": "success", "message": "Vendor onboarded successfully.", "seller_id": res["last_id"]})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/vendors/<int:seller_id>/performance', methods=['GET'])
@role_required('admin')
def vendor_performance(seller_id):
    try:
        report = call_procedure('get_vendor_performance_report', [seller_id])
        return jsonify({"status": "success", "data": report[0] if report else None})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------------------------------------------------------------------
# 4. PRODUCTS & CATEGORIES API
# ------------------------------------------------------------------------------
@app.route('/api/categories', methods=['GET'])
@role_required('admin')
def get_categories():
    cats = execute_query("SELECT * FROM Category ORDER BY category_name ASC")
    return jsonify({"status": "success", "data": cats})

@app.route('/api/products', methods=['GET', 'POST'])
@role_required('admin')
def manage_products():
    if request.method == 'GET':
        category_id = request.args.get('category_id')
        seller_id = request.args.get('seller_id')
        search = request.args.get('search', '').strip()

        conditions = ["1=1"]
        params = []

        if category_id:
            conditions.append("p.category_id = %s")
            params.append(category_id)
        if seller_id:
            conditions.append("p.seller_id = %s")
            params.append(seller_id)
        if search:
            conditions.append("(p.product_name LIKE %s OR s.seller_name LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        query = f"""
            SELECT 
                p.*,
                s.seller_name,
                c.category_name,
                ROUND(p.price * (1 - p.discount_percent/100), 2) AS discounted_price
            FROM Product p
            JOIN Seller s ON p.seller_id = s.seller_id
            JOIN Category c ON p.category_id = c.category_id
            WHERE {" AND ".join(conditions)}
            ORDER BY p.product_id DESC
        """
        products = execute_query(query, params)
        return jsonify({"status": "success", "data": products})

    elif request.method == 'POST':
        data = request.json or {}
        try:
            res = execute_dml("""
                INSERT INTO Product (product_name, seller_id, category_id, price, stock_quantity, product_rating, added_date, discount_percent)
                VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), %s)
            """, (
                data.get('product_name'),
                int(data.get('seller_id')),
                int(data.get('category_id')),
                float(data.get('price')),
                int(data.get('stock_quantity', 10)),
                float(data.get('product_rating', 4.5)),
                float(data.get('discount_percent', 0.0))
            ))
            return jsonify({"status": "success", "message": "Product listed successfully.", "product_id": res["last_id"]})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:prod_id>', methods=['PUT', 'DELETE'])
@role_required('admin')
def product_detail(prod_id):
    if request.method == 'PUT':
        data = request.json or {}
        try:
            execute_dml("""
                UPDATE Product
                SET product_name = %s, price = %s, stock_quantity = %s, discount_percent = %s
                WHERE product_id = %s
            """, (data.get('product_name'), float(data.get('price')), int(data.get('stock_quantity')), float(data.get('discount_percent', 0)), prod_id))
            return jsonify({"status": "success", "message": "Product updated successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    elif request.method == 'DELETE':
        try:
            execute_dml("DELETE FROM Product WHERE product_id = %s", (prod_id,))
            return jsonify({"status": "success", "message": "Product deleted successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

# ------------------------------------------------------------------------------
# 5. ORDERS & CHECKOUT API (Invoking Stored Procedures)
# ------------------------------------------------------------------------------
@app.route('/api/orders', methods=['GET', 'POST'])
@role_required('admin')
def manage_orders():
    if request.method == 'GET':
        orders = execute_query("""
            SELECT 
                o.order_id,
                o.order_date,
                o.total_amount,
                o.order_status,
                c.customer_id,
                CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
                c.city AS customer_city,
                p.payment_method,
                p.payment_status,
                GROUP_CONCAT(CONCAT(pr.product_name, ' (x', oi.quantity, ')') SEPARATOR ', ') AS order_summary
            FROM Orders o
            JOIN Customer c ON o.customer_id = c.customer_id
            LEFT JOIN Payment p ON o.order_id = p.order_id
            LEFT JOIN Order_Item oi ON o.order_id = oi.order_id
            LEFT JOIN Product pr ON oi.product_id = pr.product_id
            GROUP BY o.order_id, c.customer_id, p.payment_method, p.payment_status
            ORDER BY o.order_id DESC
        """)
        return jsonify({"status": "success", "data": orders})

    elif request.method == 'POST':
        # Invoke Stored Procedure: place_order_procedure
        data = request.json or {}
        cust_id = int(data.get('customer_id'))
        prod_id = int(data.get('product_id'))
        quantity = int(data.get('quantity', 1))
        payment_method = data.get('payment_method', 'UPI')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Output arguments in MySQL procedure call
            args = [cust_id, prod_id, quantity, payment_method, 0, 0, '']
            result_args = cursor.callproc('place_order_procedure', args)
            conn.commit()
            
            order_id = result_args[4]
            status_code = result_args[5]
            status_msg = result_args[6]

            if status_code == 200:
                return jsonify({"status": "success", "order_id": order_id, "message": status_msg})
            else:
                return jsonify({"status": "error", "message": status_msg}), status_code
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
@role_required('admin')
def cancel_order(order_id):
    # Invoke Stored Procedure: cancel_order_procedure
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        args = [order_id, 0, '']
        result_args = cursor.callproc('cancel_order_procedure', args)
        conn.commit()

        status_code = result_args[1]
        status_msg = result_args[2]

        if status_code == 200:
            return jsonify({"status": "success", "message": status_msg})
        else:
            return jsonify({"status": "error", "message": status_msg}), status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@role_required('admin')
def update_order_status(order_id):
    # This also fires the AFTER UPDATE trigger trg_orders_after_update_audit!
    data = request.json or {}
    new_status = data.get('status')
    if new_status not in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        return jsonify({"status": "error", "message": "Invalid status value."}), 400

    try:
        execute_dml("UPDATE Orders SET order_status = %s WHERE order_id = %s", (new_status, order_id))
        return jsonify({"status": "success", "message": f"Order #{order_id} marked as {new_status}."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ------------------------------------------------------------------------------
# 6. INVENTORY MANAGEMENT API
# ------------------------------------------------------------------------------
@app.route('/api/inventory', methods=['GET'])
@role_required('admin')
def get_inventory():
    items = execute_query("""
        SELECT 
            p.product_id,
            p.product_name,
            s.seller_name,
            c.category_name,
            p.price,
            p.stock_quantity,
            CASE 
                WHEN p.stock_quantity = 0 THEN 'OUT OF STOCK'
                WHEN p.stock_quantity <= 10 THEN 'LOW STOCK'
                ELSE 'IN STOCK'
            END AS stock_status
        FROM Product p
        JOIN Seller s ON p.seller_id = s.seller_id
        JOIN Category c ON p.category_id = c.category_id
        ORDER BY p.stock_quantity ASC
    """)
    return jsonify({"status": "success", "data": items})

@app.route('/api/inventory/update-stock', methods=['POST'])
@role_required('admin')
def update_stock():
    data = request.json or {}
    prod_id = int(data.get('product_id'))
    quantity = int(data.get('stock_quantity'))

    try:
        # Note: BEFORE UPDATE trigger trg_product_before_update will reject if < 0
        execute_dml("UPDATE Product SET stock_quantity = %s WHERE product_id = %s", (quantity, prod_id))
        return jsonify({"status": "success", "message": "Stock level updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ------------------------------------------------------------------------------
# 7. ANALYTICS & CURSOR BATCH JOBS API
# ------------------------------------------------------------------------------
@app.route('/api/analytics', methods=['GET'])
@role_required('admin')
def get_analytics():
    # Top 5 products by revenue
    top_products = execute_query("""
        SELECT 
            p.product_name,
            s.seller_name,
            SUM(oi.quantity) AS units_sold,
            SUM(oi.quantity * oi.unit_price) AS total_revenue
        FROM Order_Item oi
        JOIN Product p ON oi.product_id = p.product_id
        JOIN Seller s ON p.seller_id = s.seller_id
        JOIN Orders o ON oi.order_id = o.order_id
        WHERE o.order_status <> 'Cancelled'
        GROUP BY p.product_id, p.product_name, s.seller_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """)

    # Top spending customers
    top_customers = execute_query("""
        SELECT 
            c.customer_id,
            CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
            c.city,
            COUNT(o.order_id) AS orders_count,
            SUM(o.total_amount) AS total_spent
        FROM Orders o
        JOIN Customer c ON o.customer_id = c.customer_id
        WHERE o.order_status <> 'Cancelled'
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT 5
    """)

    # Order status breakdown
    status_breakdown = execute_query("""
        SELECT order_status, COUNT(*) AS count
        FROM Orders
        GROUP BY order_status
    """)

    return jsonify({
        "status": "success",
        "top_products": top_products,
        "top_customers": top_customers,
        "status_breakdown": status_breakdown
    })

@app.route('/api/admin/run-cursor-payouts', methods=['POST'])
@role_required('admin')
def run_cursor_payouts():
    """Triggers the calculate_vendor_payouts_cursor stored procedure!"""
    try:
        results = call_procedure('calculate_vendor_payouts_cursor')
        return jsonify({
            "status": "success",
            "message": "Vendor payouts calculated and ledger updated using MySQL Cursor.",
            "data": results
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/audit-logs', methods=['GET'])
@role_required('admin')
def get_audit_logs():
    """Retrieve audit logs generated automatically by AFTER UPDATE trigger on Orders table."""
    try:
        logs = execute_query("""
            SELECT * FROM Order_Audit_Log
            ORDER BY changed_at DESC, log_id DESC
            LIMIT 20
        """)
        return jsonify({"status": "success", "data": logs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------------------------------------------------------------------
# VENDOR APPROVAL (admin only). The full admin UI for this comes in Phase 5.
# ------------------------------------------------------------------------------
@app.route('/api/admin/vendors/<int:seller_id>/status', methods=['PUT'])
@role_required('admin')
def set_vendor_status(seller_id):
    new_status = (request.json or {}).get('status')
    if new_status not in ('Pending', 'Active', 'Inactive'):
        return jsonify({"status": "error", "message": "Status must be Pending, Active or Inactive."}), 400
    if not execute_query("SELECT seller_id FROM Seller WHERE seller_id = %s", (seller_id,), fetch_all=False):
        return jsonify({"status": "error", "message": "Vendor not found."}), 404
    execute_dml("UPDATE Seller SET status = %s WHERE seller_id = %s", (new_status, seller_id))
    return jsonify({"status": "success", "message": f"Vendor #{seller_id} is now {new_status}."})



# ------------------------------------------------------------------------------
# CUSTOMER STOREFRONT API
# All queries are scoped to the authenticated customer's customer_id.
# ------------------------------------------------------------------------------
@app.route('/api/store/products', methods=['GET'])
@role_required('customer')
def store_products():
    user = current_user()
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', '').strip()
    conditions = ["p.is_active = TRUE", "s.status = 'Active'", "p.stock_quantity >= 0"]
    params = []
    if search:
        conditions.append("(p.product_name LIKE %s OR s.seller_name LIKE %s OR c.category_name LIKE %s)")
        params.extend([f"%{search}%"] * 3)
    if category_id.isdigit():
        conditions.append("p.category_id = %s")
        params.append(int(category_id))
    try:
        rows = execute_query(f"""
            SELECT p.product_id, p.product_name, p.price, p.discount_percent,
                   ROUND(p.price * (1 - p.discount_percent / 100), 2) AS discounted_price,
                   p.stock_quantity, p.product_rating, s.seller_name, s.seller_id,
                   c.category_name, c.category_id
            FROM Product p
            JOIN Seller s ON s.seller_id = p.seller_id
            JOIN Category c ON c.category_id = p.category_id
            WHERE {' AND '.join(conditions)}
            ORDER BY p.product_id DESC
        """, tuple(params))
        categories = execute_query("SELECT category_id, category_name FROM Category ORDER BY category_name")
        return jsonify({"status": "success", "data": rows, "categories": categories})
    except Exception as e:
        return jsonify({"status": "error", "message": "Could not load products. Check the database schema."}), 500

@app.route('/api/store/cart', methods=['GET'])
@role_required('customer')
def store_get_cart():
    user = current_user()
    try:
        cart = execute_query("SELECT cart_id FROM Cart WHERE customer_id = %s", (user['customer_id'],), fetch_all=False)
        if not cart:
            return jsonify({"status": "success", "data": [], "total": 0})
        rows = execute_query("""
            SELECT ci.cart_item_id, ci.product_id, ci.quantity, p.product_name, p.price,
                   p.discount_percent, ROUND(p.price * (1 - p.discount_percent/100), 2) AS unit_price,
                   p.stock_quantity, s.seller_name
            FROM Cart_Item ci JOIN Product p ON p.product_id = ci.product_id
            JOIN Seller s ON s.seller_id = p.seller_id
            WHERE ci.cart_id = %s AND p.is_active = TRUE
            ORDER BY ci.cart_item_id DESC
        """, (cart['cart_id'],))
        total = round(sum(float(r['unit_price']) * int(r['quantity']) for r in rows), 2)
        return jsonify({"status": "success", "data": rows, "total": total})
    except Exception:
        return jsonify({"status": "error", "message": "Could not load cart."}), 500

@app.route('/api/store/cart', methods=['POST'])
@role_required('customer')
def store_add_cart():
    user = current_user()
    data = request.get_json(silent=True) or {}
    try:
        product_id, quantity = int(data.get('product_id', 0)), int(data.get('quantity', 1))
        if product_id <= 0 or quantity < 1 or quantity > 99:
            return jsonify({"status":"error","message":"Choose a valid product and quantity."}), 400
        product = execute_query("""
            SELECT p.product_id, p.stock_quantity FROM Product p
            JOIN Seller s ON s.seller_id=p.seller_id
            WHERE p.product_id=%s AND p.is_active=TRUE AND s.status='Active'
        """, (product_id,), fetch_all=False)
        if not product:
            return jsonify({"status":"error","message":"This product is unavailable."}), 404
        if quantity > product['stock_quantity']:
            return jsonify({"status":"error","message":"Quantity exceeds available stock."}), 400
        cart = execute_query("SELECT cart_id FROM Cart WHERE customer_id=%s", (user['customer_id'],), fetch_all=False)
        if not cart:
            created = execute_dml("INSERT INTO Cart (customer_id, created_date) VALUES (%s, CURDATE())", (user['customer_id'],))
            cart_id = created['last_id']
        else:
            cart_id = cart['cart_id']
        existing = execute_query("SELECT cart_item_id, quantity FROM Cart_Item WHERE cart_id=%s AND product_id=%s LIMIT 1", (cart_id, product_id), fetch_all=False)
        new_quantity = quantity + (int(existing['quantity']) if existing else 0)
        if new_quantity > product['stock_quantity']:
            return jsonify({"status":"error","message":"Your cart quantity would exceed available stock."}), 400
        if existing:
            execute_dml("UPDATE Cart_Item SET quantity=%s WHERE cart_item_id=%s", (new_quantity, existing['cart_item_id']))
        else:
            execute_dml("INSERT INTO Cart_Item (cart_id, product_id, quantity) VALUES (%s,%s,%s)", (cart_id, product_id, quantity))
        return jsonify({"status":"success","message":"Added to cart."})
    except (TypeError, ValueError):
        return jsonify({"status":"error","message":"Invalid product or quantity."}), 400
    except Exception:
        return jsonify({"status":"error","message":"Could not update cart."}), 500

@app.route('/api/store/cart/<int:item_id>', methods=['PUT', 'DELETE'])
@role_required('customer')
def store_cart_item(item_id):
    user = current_user()
    item = execute_query("""
        SELECT ci.cart_item_id, ci.quantity, ci.product_id, c.cart_id, p.stock_quantity
        FROM Cart_Item ci JOIN Cart c ON c.cart_id=ci.cart_id
        JOIN Product p ON p.product_id=ci.product_id
        WHERE ci.cart_item_id=%s AND c.customer_id=%s
    """, (item_id, user['customer_id']), fetch_all=False)
    if not item:
        return jsonify({"status":"error","message":"Cart item not found."}), 404
    if request.method == 'DELETE':
        execute_dml("DELETE FROM Cart_Item WHERE cart_item_id=%s", (item_id,))
        return jsonify({"status":"success","message":"Item removed."})
    data = request.get_json(silent=True) or {}
    try:
        qty = int(data.get('quantity', 0))
        if qty < 1 or qty > int(item['stock_quantity']):
            return jsonify({"status":"error","message":"Quantity must be between 1 and available stock."}), 400
        execute_dml("UPDATE Cart_Item SET quantity=%s WHERE cart_item_id=%s", (qty,item_id))
        return jsonify({"status":"success","message":"Quantity updated."})
    except (TypeError, ValueError):
        return jsonify({"status":"error","message":"Invalid quantity."}), 400

@app.route('/api/store/addresses', methods=['GET', 'POST'])
@role_required('customer')
def store_addresses():
    user = current_user()
    if request.method == 'GET':
        rows = execute_query("SELECT address_id,address_line,city,state,pincode,is_default FROM Customer_Address WHERE customer_id=%s ORDER BY is_default DESC,address_id DESC", (user['customer_id'],))
        return jsonify({"status":"success","data":rows})
    data = request.get_json(silent=True) or {}
    fields = [str(data.get(k,'')).strip() for k in ('address_line','city','state','pincode')]
    if not all(fields):
        return jsonify({"status":"error","message":"Address, city, state and PIN code are required."}), 400
    try:
        count = execute_query("SELECT COUNT(*) AS n FROM Customer_Address WHERE customer_id=%s", (user['customer_id'],), fetch_all=False)['n']
        res = execute_dml("""INSERT INTO Customer_Address (customer_id,address_line,city,state,pincode,is_default)
                            VALUES (%s,%s,%s,%s,%s,%s)""",
                          (user['customer_id'], *fields, 1 if count == 0 else 0))
        return jsonify({"status":"success","address_id":res['last_id'],"message":"Address saved."})
    except Exception:
        return jsonify({"status":"error","message":"Could not save address."}), 400

@app.route('/api/store/checkout', methods=['POST'])
@role_required('customer')
def store_checkout():
    user = current_user()
    data = request.get_json(silent=True) or {}
    try:
        address_id = int(data.get('address_id', 0))
        raw_method = str(data.get('payment_method', 'COD')).strip().lower()
        method_map = {'upi':'UPI', 'credit card':'Credit Card', 'debit card':'Debit Card',
                      'net banking':'Net Banking', 'cod':'COD'}
        method = method_map.get(raw_method)
        if not method:
            return jsonify({"status":"error","message":"Choose a valid payment method."}), 400
        owns = execute_query("SELECT address_id FROM Customer_Address WHERE address_id=%s AND customer_id=%s",
                             (address_id,user['customer_id']),fetch_all=False)
        if not owns:
            return jsonify({"status":"error","message":"Choose one of your saved delivery addresses."}), 400
        cart = execute_query("""SELECT c.cart_id FROM Cart c JOIN Cart_Item ci ON ci.cart_id=c.cart_id
                                WHERE c.customer_id=%s LIMIT 1""",(user['customer_id'],),fetch_all=False)
        if not cart:
            return jsonify({"status":"error","message":"Your cart is empty."}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            
            args = [user['customer_id'], address_id, method, 0, '']
            out = cur.callproc('place_order_from_cart', args)
            
            order_id, message = out[3], out[4]

            # The procedure communicates its result through the message.
            if not order_id:
                conn.rollback()
                return jsonify({
                    "status": "error",
                    "message": message or "Checkout failed."
                }), 400

            conn.commit()

            return jsonify({
                "status": "success",
                "order_id": order_id,
                "message": message or "Order placed successfully."
            })

        finally:
            cur.close()
            conn.close()
    except Exception:
        app.logger.exception("Checkout failed")
        return jsonify({
            "status": "error",
            "message": "Checkout failed. Check the server terminal."
        }), 500

@app.route('/api/store/orders', methods=['GET'])
@role_required('customer')
def store_orders():
    user = current_user()
    rows = execute_query("""
        SELECT o.order_id,o.order_date,o.total_amount,o.order_status,p.payment_method,p.payment_status,
               COUNT(oi.order_item_id) AS item_count,
               GROUP_CONCAT(CONCAT(pr.product_name,' × ',oi.quantity) SEPARATOR ', ') AS items
        FROM Orders o LEFT JOIN Payment p ON p.order_id=o.order_id
        LEFT JOIN Order_Item oi ON oi.order_id=o.order_id
        LEFT JOIN Product pr ON pr.product_id=oi.product_id
        WHERE o.customer_id=%s
        GROUP BY o.order_id,p.payment_method,p.payment_status
        ORDER BY o.order_id DESC
    """,(user['customer_id'],))
    return jsonify({"status":"success","data":rows})

# ------------------------------------------------------------------------------
# VENDOR DASHBOARD API. Every query is scoped to the logged-in seller_id.
# ------------------------------------------------------------------------------
@app.route('/api/vendor/summary', methods=['GET'])
@role_required('vendor')
def vendor_summary():
    sid=current_user()['seller_id']
    stats=execute_query("""
        SELECT COUNT(DISTINCT p.product_id) AS products,
               COALESCE(SUM(DISTINCT CASE WHEN p.stock_quantity<=10 THEN p.product_id END),0) AS low_stock_marker,
               COUNT(DISTINCT CASE WHEN oi.item_status='Pending' THEN oi.order_item_id END) AS pending_items,
               COALESCE(SUM(CASE WHEN oi.item_status<>'Cancelled' THEN oi.quantity*oi.unit_price ELSE 0 END),0) AS gross_sales
        FROM Product p LEFT JOIN Order_Item oi ON oi.product_id=p.product_id
        WHERE p.seller_id=%s
    """,(sid,),fetch_all=False)
    stats['low_stock'] = execute_query("SELECT COUNT(*) AS n FROM Product WHERE seller_id=%s AND stock_quantity<=10",(sid,),fetch_all=False)['n']
    return jsonify({"status":"success","data":stats})

@app.route('/api/vendor/categories', methods=['GET'])
@role_required('vendor')
def vendor_categories():
    return jsonify({"status":"success","data":execute_query("SELECT category_id,category_name FROM Category ORDER BY category_name")})

@app.route('/api/vendor/products', methods=['GET','POST'])
@role_required('vendor')
def vendor_products():
    sid=current_user()['seller_id']
    if request.method=='GET':
        rows=execute_query("""SELECT p.product_id,p.product_name,p.category_id,c.category_name,p.price,p.discount_percent,
                                    ROUND(p.price*(1-p.discount_percent/100),2) AS discounted_price,
                                    p.stock_quantity,p.product_rating,p.is_active
                             FROM Product p JOIN Category c ON c.category_id=p.category_id
                             WHERE p.seller_id=%s ORDER BY p.product_id DESC""",(sid,))
        return jsonify({"status":"success","data":rows})
    data=request.get_json(silent=True) or {}
    name=str(data.get('product_name','')).strip()
    try:
        category_id=int(data.get('category_id',0)); price=float(data.get('price',0))
        stock=int(data.get('stock_quantity',0)); discount=float(data.get('discount_percent',0))
        if not name or category_id<=0 or price<=0 or stock<0 or not 0<=discount<=100:
            return jsonify({"status":"error","message":"Enter a product name, category, positive price, valid stock and 0–100 discount."}),400
        cat=execute_query("SELECT category_id FROM Category WHERE category_id=%s",(category_id,),fetch_all=False)
        if not cat: return jsonify({"status":"error","message":"Category not found."}),400
        res=execute_dml("""INSERT INTO Product (product_name,seller_id,category_id,price,stock_quantity,product_rating,added_date,discount_percent,is_active)
                           VALUES (%s,%s,%s,%s,%s,0,CURDATE(),%s,TRUE)""",
                         (name,sid,category_id,price,stock,discount))
        return jsonify({"status":"success","product_id":res['last_id'],"message":"Product added."})
    except (TypeError,ValueError):
        return jsonify({"status":"error","message":"Invalid product values."}),400
    except Exception:
        return jsonify({"status":"error","message":"Could not save product."}),400

@app.route('/api/vendor/products/<int:product_id>', methods=['PUT'])
@role_required('vendor')
def vendor_update_product(product_id):
    sid=current_user()['seller_id']
    data=request.get_json(silent=True) or {}
    try:
        name=str(data.get('product_name','')).strip()
        price=float(data.get('price',0)); stock=int(data.get('stock_quantity',-1)); discount=float(data.get('discount_percent',0))
        if not name or price<=0 or stock<0 or not 0<=discount<=100:
            return jsonify({"status":"error","message":"Enter valid product details."}),400
        result=execute_dml("""UPDATE Product SET product_name=%s,price=%s,stock_quantity=%s,discount_percent=%s
                              WHERE product_id=%s AND seller_id=%s""",(name,price,stock,discount,product_id,sid))
        if not result['affected_rows']:
            return jsonify({"status":"error","message":"Product not found or not yours."}),404
        return jsonify({"status":"success","message":"Product updated."})
    except (TypeError,ValueError):
        return jsonify({"status":"error","message":"Invalid product values."}),400
    except Exception:
        return jsonify({"status":"error","message":"Could not update product."}),400

@app.route('/api/vendor/orders', methods=['GET'])
@role_required('vendor')
def vendor_orders():
    sid=current_user()['seller_id']
    rows=execute_query("""
        SELECT oi.order_item_id,oi.order_id,oi.product_id,pr.product_name,oi.quantity,oi.unit_price,
               oi.item_status,o.order_date,o.order_status,CONCAT(c.first_name,' ',c.last_name) AS customer_name,
               ca.city,ca.state
        FROM Order_Item oi JOIN Product pr ON pr.product_id=oi.product_id
        JOIN Orders o ON o.order_id=oi.order_id JOIN Customer c ON c.customer_id=o.customer_id
        LEFT JOIN Customer_Address ca ON ca.address_id=o.address_id
        WHERE pr.seller_id=%s ORDER BY o.order_id DESC,oi.order_item_id DESC
    """,(sid,))
    return jsonify({"status":"success","data":rows})

@app.route('/api/vendor/orders/<int:item_id>/status', methods=['PUT'])
@role_required('vendor')
def vendor_update_item_status(item_id):
    sid=current_user()['seller_id']
    data=request.get_json(silent=True) or {}
    status=data.get('status')
    if status not in ('Pending','Shipped','Delivered','Cancelled'):
        return jsonify({"status":"error","message":"Invalid item status."}),400
    item=execute_query("""SELECT oi.order_item_id,oi.order_id,oi.item_status
                          FROM Order_Item oi JOIN Product p ON p.product_id=oi.product_id
                          WHERE oi.order_item_id=%s AND p.seller_id=%s""",(item_id,sid),fetch_all=False)
    if not item: return jsonify({"status":"error","message":"Order item not found or not yours."}),404
    try:
        execute_dml("UPDATE Order_Item SET item_status=%s WHERE order_item_id=%s",(status,item_id))
        # Derive the parent order status from all item statuses, preserving mixed-vendor fulfilment.
        statuses=execute_query("SELECT item_status FROM Order_Item WHERE order_id=%s",(item['order_id'],))
        vals={r['item_status'] for r in statuses}
        parent='Delivered' if vals=={'Delivered'} else ('Shipped' if vals.issubset({'Shipped','Delivered'}) and 'Shipped' in vals else ('Cancelled' if vals=={'Cancelled'} else ('Processing' if any(v!='Pending' for v in vals) else 'Pending')))
        execute_dml("UPDATE Orders SET order_status=%s WHERE order_id=%s",(parent,item['order_id']))
        return jsonify({"status":"success","message":"Order item status updated."})
    except Exception:
        return jsonify({"status":"error","message":"Could not update order item status."}),400


if __name__ == '__main__':
    print("Starting Smart Multi-Vendor E-Commerce Backend on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)

