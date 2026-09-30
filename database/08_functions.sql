-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 08_functions.sql
-- Description: Stored Functions for Mathematical & Business Logic (Lab 6)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

DELIMITER //

-- ==============================================================================
-- 1. FUNCTION: CALCULATE ORDER SUBTOTAL
-- Objective: Dynamically computes total sum of line items for a given order.
-- Characteristics: READS SQL DATA, NOT DETERMINISTIC (data may change)
-- ==============================================================================
DROP FUNCTION IF EXISTS calculate_order_subtotal//
CREATE FUNCTION calculate_order_subtotal(p_order_id INT)
RETURNS DECIMAL(10,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_subtotal DECIMAL(10,2) DEFAULT 0.00;

    SELECT COALESCE(SUM(quantity * unit_price), 0.00)
    INTO v_subtotal
    FROM Order_Item
    WHERE order_id = p_order_id;

    RETURN v_subtotal;
END //

-- ==============================================================================
-- 2. FUNCTION: CALCULATE DISCOUNTED PRICE
-- Objective: Pure mathematical formula to compute net price after discount percentage.
-- Characteristics: DETERMINISTIC, NO SQL (Executes in-memory at high speed)
-- ==============================================================================
DROP FUNCTION IF EXISTS calculate_discounted_price//
CREATE FUNCTION calculate_discounted_price(
    p_base_price DECIMAL(10,2),
    p_discount_percentage DECIMAL(5,2)
)
RETURNS DECIMAL(10,2)
DETERMINISTIC
NO SQL
BEGIN
    DECLARE v_final_price DECIMAL(10,2);
    
    IF p_discount_percentage <= 0 THEN
        RETURN p_base_price;
    ELSEIF p_discount_percentage >= 100 THEN
        RETURN 0.00;
    END IF;

    SET v_final_price = ROUND(p_base_price * (1 - (p_discount_percentage / 100.0)), 2);
    RETURN v_final_price;
END //

-- ==============================================================================
-- 3. FUNCTION: CALCULATE VENDOR COMMISSION
-- Objective: Calculates marketplace platform commission cut based on vendor's specific contract rate.
-- ==============================================================================
DROP FUNCTION IF EXISTS calculate_vendor_commission//
CREATE FUNCTION calculate_vendor_commission(
    p_seller_id INT,
    p_sale_amount DECIMAL(10,2)
)
RETURNS DECIMAL(10,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_rate DECIMAL(4,2) DEFAULT 10.00;
    DECLARE v_commission DECIMAL(10,2);

    SELECT commission_rate INTO v_rate
    FROM Seller
    WHERE seller_id = p_seller_id;

    IF v_rate IS NULL THEN
        SET v_rate = 10.00;
    END IF;

    SET v_commission = ROUND(p_sale_amount * (v_rate / 100.0), 2);
    RETURN v_commission;
END //

-- ==============================================================================
-- 4. FUNCTION: GET CUSTOMER LIFETIME SPENDING (LTV)
-- Objective: Evaluates total verified spending of a customer across delivered orders.
-- ==============================================================================
DROP FUNCTION IF EXISTS get_customer_spending//
CREATE FUNCTION get_customer_spending(p_customer_id INT)
RETURNS DECIMAL(10,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_total DECIMAL(10,2) DEFAULT 0.00;

    SELECT COALESCE(SUM(total_amount), 0.00)
    INTO v_total
    FROM Orders
    WHERE customer_id = p_customer_id
      AND order_status = 'Delivered';

    RETURN v_total;
END //

DELIMITER ;

-- ==============================================================================
-- VERIFICATION QUERIES DEMONSTRATING FUNCTION CALLS IN DQL
-- ==============================================================================
SELECT 
    product_name,
    price AS original_price,
    discount_percent,
    calculate_discounted_price(price, discount_percent) AS net_price
FROM Product
LIMIT 5;

SELECT 
    order_id,
    total_amount AS recorded_total,
    calculate_order_subtotal(order_id) AS computed_subtotal
FROM Orders
LIMIT 5;
