-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 10_views_and_indexing.sql
-- Description: Views, Updatable Views, Indexing & EXPLAIN Execution Plans (Lab 8 & Unit 5)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

-- ==============================================================================
-- 1. INDEXING FOR QUERY OPTIMIZATION
-- Speeds up search, range scans, and join lookups in high-cardinality e-commerce tables.
-- ==============================================================================

-- Index on frequently filtered product price column
CREATE INDEX idx_product_price ON Product(price);

-- Composite index on customer city and status for localized customer targeting
CREATE INDEX idx_customer_city_status ON Customer(city, status);

-- Index on order date for fast temporal range reporting
CREATE INDEX idx_orders_order_date ON Orders(order_date);

-- Composite index on Order_Item for lightning fast joins
CREATE INDEX idx_order_item_composite ON Order_Item(order_id, product_id);

-- ==============================================================================
-- 2. QUERY PROCESSING & EXECUTION PLAN ANALYSIS (EXPLAIN)
-- Demonstrates query optimization, index usage, and cost estimation.
-- ==============================================================================

-- Query 1: Filter by product price using B-Tree index
EXPLAIN 
SELECT product_id, product_name, price 
FROM Product 
WHERE price BETWEEN 1000.00 AND 5000.00;

-- Query 2: Multi-table join execution plan analysis
EXPLAIN
SELECT 
    o.order_id,
    c.first_name,
    p.product_name,
    s.seller_name
FROM Orders o
INNER JOIN Customer c ON o.customer_id = c.customer_id
INNER JOIN Order_Item oi ON o.order_id = oi.order_id
INNER JOIN Product p ON oi.product_id = p.product_id
INNER JOIN Seller s ON p.seller_id = s.seller_id
WHERE o.order_date >= '2025-06-01';

-- ==============================================================================
-- 3. COMPLEX MULTI-TABLE VIEW (Read-Only Analytical View)
-- Scenario: Unified order fulfillment dashboard view joining 5 tables.
-- ==============================================================================
CREATE OR REPLACE VIEW view_order_details AS
SELECT 
    o.order_id,
    o.order_date,
    o.order_status,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.email AS customer_email,
    c.city AS customer_city,
    p.product_name,
    cat.category_name,
    s.seller_name AS vendor_name,
    oi.quantity,
    oi.unit_price,
    (oi.quantity * oi.unit_price) AS line_total,
    py.payment_method,
    py.payment_status
FROM Orders o
INNER JOIN Customer c ON o.customer_id = c.customer_id
INNER JOIN Order_Item oi ON o.order_id = oi.order_id
INNER JOIN Product p ON oi.product_id = p.product_id
INNER JOIN Category cat ON p.category_id = cat.category_id
INNER JOIN Seller s ON p.seller_id = s.seller_id
LEFT JOIN Payment py ON o.order_id = py.order_id;

-- Querying the multi-table view
SELECT * FROM view_order_details LIMIT 10;

-- ==============================================================================
-- 4. UPDATABLE VIEW (Single Base Table with WITH CHECK OPTION)
-- Lab 8 Requirement: Demonstrate updating a base table through an updatable view
-- and demonstrate restrictions using WITH CHECK OPTION.
-- ==============================================================================
CREATE OR REPLACE VIEW view_active_electronics AS
SELECT 
    product_id,
    product_name,
    seller_id,
    category_id,
    price,
    stock_quantity
FROM Product
WHERE category_id = 1
WITH CHECK OPTION;

-- Select through view
SELECT * FROM view_active_electronics;

-- Updatable view DML Test: Update price of Product 2 through view
UPDATE view_active_electronics
SET price = 1299.00
WHERE product_id = 2;

-- Verify change propagated to underlying base table 'Product'
SELECT product_id, product_name, price 
FROM Product 
WHERE product_id = 2;

-- View restriction test:
-- Trying to update category_id to 2 through view_active_electronics will FAIL
-- because WITH CHECK OPTION guarantees rows must satisfy 'WHERE category_id = 1'.
-- (Uncomment to test failure: UPDATE view_active_electronics SET category_id = 2 WHERE product_id = 2;)
