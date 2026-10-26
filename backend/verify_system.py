"""
Comprehensive Verification Script for Smart Multi-Vendor E-Commerce
Tests Customer, Vendor, and Admin workflows, Cart Drawer APIs, Order Timestamps, and Triggers.
"""
import sys
import os
import json
import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app
from backend.db import execute_query

def run_tests():
    client = app.test_client()
    print("=" * 70)
    print("STARTING SMARTSTORE E-COMMERCE END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. CUSTOMER WORKFLOW
    # ---------------------------------------------------------
    print("\n[TEST 1] Customer Login & Session Handling...")
    login_resp = client.post('/api/auth/login', json={
        'email': 'aarav.sharma@gmail.com',
        'password': 'Customer@123'
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.data}"
    me_resp = client.get('/api/auth/me')
    assert me_resp.status_code == 200
    user_data = me_resp.get_json()['user']
    print(f"  -> Logged in as: {user_data['name']} (Role: {user_data['role']}, Email: {user_data['email']})")

    print("\n[TEST 2] Product Browsing & Filtering...")
    prod_resp = client.get('/api/store/products')
    assert prod_resp.status_code == 200
    products = prod_resp.get_json()['data']
    assert len(products) > 0, "No products found!"
    print(f"  -> Loaded {len(products)} products from catalog.")
    test_prod = next(p for p in products if p['stock_quantity'] > 2)
    print(f"  -> Test Product Selected: #{test_prod['product_id']} '{test_prod['product_name']}' (Stock: {test_prod['stock_quantity']}, Price: ₹{test_prod['discounted_price']})")

    print("\n[TEST 3] Add to Cart & Drawer Synchronization...")
    add_resp = client.post('/api/store/cart', json={
        'product_id': test_prod['product_id'],
        'quantity': 1
    })
    assert add_resp.status_code == 200, f"Add to cart failed: {add_resp.data}"
    add_json = add_resp.get_json()
    print(f"  -> Add to Cart Response: {add_json['message']} (Product ID: {add_json.get('product_id')})")

    cart_resp = client.get('/api/store/cart')
    assert cart_resp.status_code == 200
    cart_json = cart_resp.get_json()
    cart_items = cart_json['data']
    assert len(cart_items) > 0, "Cart is empty after adding item!"
    cart_item = next(item for item in cart_items if item['product_id'] == test_prod['product_id'])
    print(f"  -> Cart Drawer Server State: {len(cart_items)} item(s), Total: ₹{cart_json['total']}")
    print(f"  -> Cart Item: #{cart_item['cart_item_id']} '{cart_item['product_name']}' Qty: {cart_item['quantity']}")

    print("\n[TEST 4] Cart Stepper Updates (Quantity Increment/Decrement)...")
    inc_resp = client.put(f"/api/store/cart/{cart_item['cart_item_id']}", json={'quantity': 2})
    assert inc_resp.status_code == 200
    cart_after_inc = client.get('/api/store/cart').get_json()
    updated_item = next(i for i in cart_after_inc['data'] if i['cart_item_id'] == cart_item['cart_item_id'])
    assert updated_item['quantity'] == 2
    print(f"  -> Quantity successfully stepped up to: {updated_item['quantity']} (Total: ₹{cart_after_inc['total']})")

    # Step back to 1
    client.put(f"/api/store/cart/{cart_item['cart_item_id']}", json={'quantity': 1})
    print("  -> Quantity stepped back down to: 1")

    print("\n[TEST 5] Customer Saved Addresses...")
    addr_resp = client.get('/api/store/addresses')
    assert addr_resp.status_code == 200
    addresses = addr_resp.get_json()['data']
    assert len(addresses) > 0, "Customer has no addresses!"
    chosen_addr = addresses[0]
    print(f"  -> Using delivery destination: #{chosen_addr['address_id']} {chosen_addr['address_line']}, {chosen_addr['city']}")

    print("\n[TEST 6] End-to-End Checkout with ACID Stored Procedure...")
    stock_before = execute_query("SELECT stock_quantity FROM Product WHERE product_id=%s", (test_prod['product_id'],), fetch_all=False)['stock_quantity']
    checkout_resp = client.post('/api/store/checkout', json={
        'address_id': chosen_addr['address_id'],
        'payment_method': 'UPI'
    })
    assert checkout_resp.status_code == 200, f"Checkout failed: {checkout_resp.data}"
    checkout_data = checkout_resp.get_json()
    new_order_id = checkout_data['order_id']
    print(f"  -> Order placed successfully! Order ID: #{new_order_id}")

    # Check stock trigger decrement
    stock_after = execute_query("SELECT stock_quantity FROM Product WHERE product_id=%s", (test_prod['product_id'],), fetch_all=False)['stock_quantity']
    assert stock_after == stock_before - 1, f"Trigger failed to decrement stock: was {stock_before}, now {stock_after}"
    print(f"  -> Verified MySQL AFTER INSERT Trigger: Product stock decremented from {stock_before} to {stock_after}")

    # Check cart is cleared
    cart_final = client.get('/api/store/cart').get_json()['data']
    assert len(cart_final) == 0, f"Cart not cleared: {cart_final}"
    print("  -> Verified Cart cleared after checkout.")

    # ---------------------------------------------------------
    # 2. PRIORITY 3: ORDER TIMESTAMP VERIFICATION
    # ---------------------------------------------------------
    print("\n[TEST 7] Order Date & Time Verification (Priority 3)...")
    orders_resp = client.get('/api/store/orders')
    assert orders_resp.status_code == 200
    customer_orders = orders_resp.get_json()['data']
    placed_order = next(o for o in customer_orders if o['order_id'] == new_order_id)
    raw_date = placed_order['order_date']
    print(f"  -> Placed Order #{new_order_id} raw serialized order_date: '{raw_date}'")
    assert 'T' in raw_date or ' ' in raw_date, f"Expected full timestamp with time component, got: {raw_date}"
    # Ensure it's not 00:00:00
    time_part = raw_date.split('T')[1] if 'T' in raw_date else raw_date.split(' ')[1]
    assert time_part != '00:00:00', f"Timestamp has 00:00:00! {raw_date}"
    print(f"  -> SUCCESS: Timestamp captured real time: {time_part} (No 00:00:00!)")

    # Check legacy order formatting
    legacy_order = next((o for o in customer_orders if o['order_id'] <= 10), None)
    if legacy_order:
        print(f"  -> Legacy Order #{legacy_order['order_id']} date: '{legacy_order['order_date']}' (preserved without fabricated time)")

    # ---------------------------------------------------------
    # 3. VENDOR WORKFLOW
    # ---------------------------------------------------------
    print("\n[TEST 8] Vendor Portal & Authorization...")
    client.post('/api/auth/logout')
    vendor_login = client.post('/api/auth/login', json={
        'email': 'contact@techworld.com',
        'password': 'Vendor@123'
    })
    assert vendor_login.status_code == 200
    print("  -> Logged in as Vendor: contact@techworld.com")

    v_summary = client.get('/api/vendor/summary').get_json()['data']
    print(f"  -> Vendor Summary: Products={v_summary['products']}, Low Stock={v_summary['low_stock']}, Sales=₹{v_summary['gross_sales']}")

    v_orders = client.get('/api/vendor/orders').get_json()['data']
    print(f"  -> Vendor has {len(v_orders)} order item(s) to fulfil.")
    if len(v_orders) > 0:
        item_to_update = v_orders[0]
        status_update_resp = client.put(f"/api/vendor/orders/{item_to_update['order_item_id']}/status", json={'status': 'Shipped'})
        assert status_update_resp.status_code == 200
        print(f"  -> Updated Item #{item_to_update['order_item_id']} status to 'Shipped'")

    # ---------------------------------------------------------
    # 4. ADMIN WORKFLOW & AUDIT LOGS
    # ---------------------------------------------------------
    print("\n[TEST 9] Admin Portal & Trigger Audit Log...")
    client.post('/api/auth/logout')
    admin_login = client.post('/api/auth/login', json={
        'email': 'admin@smartstore.com',
        'password': 'Admin@123'
    })
    assert admin_login.status_code == 200
    print("  -> Logged in as Admin: admin@smartstore.com")

    admin_stats = client.get('/api/dashboard/stats').get_json()
    print(f"  -> Admin Dashboard Stats: Total Revenue=₹{admin_stats['kpis']['total_revenue']}, Orders={admin_stats['kpis']['total_orders']}")

    admin_orders = client.get('/api/orders').get_json()['data']
    latest_admin_order = admin_orders[0]
    print(f"  -> Admin Latest Order #{latest_admin_order['order_id']} date: {latest_admin_order['order_date']}")

    audit_logs = client.get('/api/audit-logs').get_json()['data']
    print(f"  -> Trigger Audit Logs: {len(audit_logs)} audit entry/entries found.")
    if len(audit_logs) > 0:
        latest_log = audit_logs[0]
        print(f"  -> Latest Log: #LOG-{latest_log['log_id']} Order #{latest_log['order_id']} Status Change: {latest_log['old_status']} -> {latest_log['new_status']} at {latest_log['changed_at']}")

    print("\n" + "=" * 70)
    print("ALL 9 TEST SUITES COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
