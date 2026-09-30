import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, jsonify, request, render_template, send_from_directory
from backend.config import Config
from backend.db import execute_query, execute_dml, call_procedure, get_db_connection

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'static')
)
app.config.from_object(Config)

# ------------------------------------------------------------------------------
# FRONTEND ROUTES
# ------------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ------------------------------------------------------------------------------
# 1. DASHBOARD & SUMMARY METRICS API
# ------------------------------------------------------------------------------
@app.route('/api/dashboard/stats', methods=['GET'])
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
        phone = data.get('phone', '').strip()
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
        try:
            execute_dml("DELETE FROM Customer WHERE customer_id = %s", (cust_id,))
            return jsonify({"status": "success", "message": "Customer removed successfully."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

# ------------------------------------------------------------------------------
# 3. VENDORS / SELLERS API
# ------------------------------------------------------------------------------
@app.route('/api/vendors', methods=['GET', 'POST'])
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
def get_categories():
    cats = execute_query("SELECT * FROM Category ORDER BY category_name ASC")
    return jsonify({"status": "success", "data": cats})

@app.route('/api/products', methods=['GET', 'POST'])
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

if __name__ == '__main__':
    print("Starting Smart Multi-Vendor E-Commerce Backend on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
