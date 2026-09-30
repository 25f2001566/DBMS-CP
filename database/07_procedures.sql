-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 07_procedures.sql
-- Description: Stored Procedures for Business Operations & Transactions (Lab 6)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

DELIMITER //

-- ==============================================================================
-- 1. PROCEDURE: PLACE ORDER (With Transaction Management & Stock Checking)
-- Objective: End-to-end checkout with ACID transaction semantics.
-- Demonstrates: IN/OUT parameters, conditional branching, START TRANSACTION,
--               COMMIT, ROLLBACK, exception handling.
-- ==============================================================================
DROP PROCEDURE IF EXISTS place_order_procedure//
CREATE PROCEDURE place_order_procedure(
    IN p_customer_id INT,
    IN p_product_id INT,
    IN p_quantity INT,
    IN p_payment_method VARCHAR(30),
    OUT p_order_id INT,
    OUT p_status_code INT,
    OUT p_status_message VARCHAR(255)
)
proc_body: BEGIN
    DECLARE v_available_stock INT DEFAULT 0;
    DECLARE v_unit_price DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_total_cost DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_customer_status VARCHAR(20);

    -- Error Handler for unexpected SQLEXCEPTION
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_order_id = 0;
        SET p_status_code = 500;
        SET p_status_message = 'Database Error: Transaction rolled back successfully.';
    END;

    -- Validate Customer
    SELECT status INTO v_customer_status 
    FROM Customer 
    WHERE customer_id = p_customer_id;

    IF v_customer_status IS NULL THEN
        SET p_order_id = 0;
        SET p_status_code = 404;
        SET p_status_message = 'Order placement failed: Customer not found.';
        LEAVE proc_body;
    ELSEIF v_customer_status <> 'Active' THEN
        SET p_order_id = 0;
        SET p_status_code = 403;
        SET p_status_message = 'Order placement failed: Customer account is Inactive.';
        LEAVE proc_body;
    END IF;

    -- Check Product & Stock
    SELECT stock_quantity, price INTO v_available_stock, v_unit_price
    FROM Product
    WHERE product_id = p_product_id;

    IF v_unit_price IS NULL THEN
        SET p_order_id = 0;
        SET p_status_code = 404;
        SET p_status_message = 'Order placement failed: Product not found.';
        LEAVE proc_body;
    END IF;

    IF v_available_stock < p_quantity THEN
        SET p_order_id = 0;
        SET p_status_code = 400;
        SET p_status_message = CONCAT('Order failed: Insufficient stock. Only ', v_available_stock, ' units available.');
        LEAVE proc_body;
    END IF;

    -- Compute Total
    SET v_total_cost = v_unit_price * p_quantity;

    -- ATOMIC TRANSACTION EXECUTION
    START TRANSACTION;

        -- 1. Insert Orders master row
        INSERT INTO Orders (customer_id, order_date, total_amount, order_status)
        VALUES (p_customer_id, CURDATE(), v_total_cost, 'Processing');
        
        SET p_order_id = LAST_INSERT_ID();

        -- 2. Insert Order_Item row
        INSERT INTO Order_Item (order_id, product_id, quantity, unit_price)
        VALUES (p_order_id, p_product_id, p_quantity, v_unit_price);

        -- 3. Stock decrement is handled automatically by AFTER INSERT trigger on Order_Item!
        -- Or directly updated here if triggers are not yet loaded:
        UPDATE Product 
        SET stock_quantity = stock_quantity - p_quantity
        WHERE product_id = p_product_id;

        -- 4. Insert Payment record
        INSERT INTO Payment (order_id, payment_date, payment_method, payment_status)
        VALUES (
            p_order_id, 
            IF(p_payment_method = 'COD', NULL, CURDATE()),
            p_payment_method,
            IF(p_payment_method = 'COD', 'Pending', 'Completed')
        );

    COMMIT;

    SET p_status_code = 200;
    SET p_status_message = CONCAT('Order #', p_order_id, ' placed successfully for total Rs. ', v_total_cost);
END //

-- ==============================================================================
-- 2. PROCEDURE: CANCEL ORDER & RESTORE INVENTORY
-- Objective: Safely cancel an order, reverse product inventory, and issue refund status.
-- ==============================================================================
DROP PROCEDURE IF EXISTS cancel_order_procedure//
CREATE PROCEDURE cancel_order_procedure(
    IN p_order_id INT,
    OUT p_status_code INT,
    OUT p_status_message VARCHAR(255)
)
proc_cancel: BEGIN
    DECLARE v_current_status VARCHAR(30);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status_code = 500;
        SET p_status_message = 'Database Error: Cancellation transaction rolled back.';
    END;

    -- Check current order status
    SELECT order_status INTO v_current_status
    FROM Orders
    WHERE order_id = p_order_id;

    IF v_current_status IS NULL THEN
        SET p_status_code = 404;
        SET p_status_message = 'Cancellation failed: Order does not exist.';
        LEAVE proc_cancel;
    END IF;

    IF v_current_status = 'Delivered' THEN
        SET p_status_code = 400;
        SET p_status_message = 'Cancellation failed: Order is already Delivered and cannot be cancelled.';
        LEAVE proc_cancel;
    END IF;

    IF v_current_status = 'Cancelled' THEN
        SET p_status_code = 400;
        SET p_status_message = 'Order is already marked as Cancelled.';
        LEAVE proc_cancel;
    END IF;

    START TRANSACTION;

        -- 1. Restore product stock quantities
        UPDATE Product p
        INNER JOIN Order_Item oi ON p.product_id = oi.product_id
        SET p.stock_quantity = p.stock_quantity + oi.quantity
        WHERE oi.order_id = p_order_id;

        -- 2. Update order status
        UPDATE Orders
        SET order_status = 'Cancelled'
        WHERE order_id = p_order_id;

        -- 3. Update payment status to Refunded if completed, or Failed
        UPDATE Payment
        SET payment_status = IF(payment_status = 'Completed', 'Refunded', 'Failed')
        WHERE order_id = p_order_id;

    COMMIT;

    SET p_status_code = 200;
    SET p_status_message = CONCAT('Order #', p_order_id, ' cancelled successfully. Stock has been restored.');
END //

-- ==============================================================================
-- 3. PROCEDURE: GENERATE VENDOR SALES PERFORMANCE SUMMARY
-- Objective: Real-time analytics report for a specific vendor.
-- ==============================================================================
DROP PROCEDURE IF EXISTS get_vendor_performance_report//
CREATE PROCEDURE get_vendor_performance_report(IN p_seller_id INT)
BEGIN
    SELECT 
        s.seller_id,
        s.seller_name,
        s.rating,
        s.commission_rate,
        COUNT(DISTINCT p.product_id) AS active_catalog_products,
        COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
        COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS gross_sales_amount,
        ROUND(COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) * (s.commission_rate / 100), 2) AS platform_commission,
        ROUND(COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) * (1 - s.commission_rate / 100), 2) AS net_vendor_earnings
    FROM Seller s
    LEFT JOIN Product p ON s.seller_id = p.seller_id
    LEFT JOIN Order_Item oi ON p.product_id = oi.product_id
    LEFT JOIN Orders o ON oi.order_id = o.order_id AND o.order_status <> 'Cancelled'
    WHERE s.seller_id = p_seller_id
    GROUP BY s.seller_id, s.seller_name, s.rating, s.commission_rate;
END //

DELIMITER ;
