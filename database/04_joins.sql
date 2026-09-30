-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 04_joins.sql
-- Description: Join Queries for Multi-Vendor Operations & Reporting (Lab 4)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

-- ==============================================================================
-- 1. EQUIJOIN (Equal condition on related keys)
-- Scenario: Find which customer placed which order and the total amount.
-- ==============================================================================
SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    o.order_id,
    o.order_date,
    o.total_amount,
    o.order_status
FROM Customer c
INNER JOIN Orders o ON c.customer_id = o.customer_id;

-- Scenario 2: Show each product alongside its verified selling vendor.
SELECT 
    p.product_id,
    p.product_name,
    p.price,
    s.seller_name,
    s.rating AS seller_rating
FROM Product p
INNER JOIN Seller s ON p.seller_id = s.seller_id;

-- ==============================================================================
-- 2. NON-EQUIJOIN (Join condition using inequality / range operators)
-- Scenario: Categorize each product into a market segment price band
-- without using hardcoded values, by joining with the Price_Range reference table.
-- ==============================================================================
SELECT 
    p.product_id,
    p.product_name,
    p.price,
    r.range_name,
    r.minimum_price,
    r.maximum_price
FROM Product p
INNER JOIN Price_Range r 
    ON p.price BETWEEN r.minimum_price AND r.maximum_price
ORDER BY p.price DESC;

-- ==============================================================================
-- 3. SELF-JOIN (Joining a table to itself)
-- Scenario: Find pairs of distinct customers who live in the exact same city.
-- c1.customer_id < c2.customer_id ensures no duplicates (A, B) and (B, A), and excludes (A, A).
-- ==============================================================================
SELECT 
    c1.city,
    c1.customer_id AS customer_1_id,
    CONCAT(c1.first_name, ' ', c1.last_name) AS customer_1,
    c2.customer_id AS customer_2_id,
    CONCAT(c2.first_name, ' ', c2.last_name) AS customer_2
FROM Customer c1
INNER JOIN Customer c2 
    ON c1.city = c2.city 
    AND c1.customer_id < c2.customer_id
ORDER BY c1.city;

-- ==============================================================================
-- 4. MULTI-TABLE INNER JOIN (Deep Multi-Vendor Line Item Tracking)
-- Scenario: Trace an order down to customer, product, category, and vendor details.
-- ==============================================================================
SELECT 
    o.order_id,
    o.order_date,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    p.product_name,
    cat.category_name,
    s.seller_name AS vendor,
    oi.quantity,
    oi.unit_price,
    (oi.quantity * oi.unit_price) AS line_total,
    o.order_status
FROM Orders o
INNER JOIN Customer c ON o.customer_id = c.customer_id
INNER JOIN Order_Item oi ON o.order_id = oi.order_id
INNER JOIN Product p ON oi.product_id = p.product_id
INNER JOIN Category cat ON p.category_id = cat.category_id
INNER JOIN Seller s ON p.seller_id = s.seller_id
ORDER BY o.order_id, oi.order_item_id;

-- ==============================================================================
-- 5. LEFT OUTER JOIN
-- Scenario: List ALL sellers, showing their product catalog count and sales,
-- including new sellers who have not listed any items or made any sales.
-- ==============================================================================
SELECT 
    s.seller_id,
    s.seller_name,
    s.city,
    s.rating,
    COUNT(p.product_id) AS total_products_listed,
    COALESCE(SUM(p.stock_quantity), 0) AS total_inventory_units
FROM Seller s
LEFT JOIN Product p ON s.seller_id = p.seller_id
GROUP BY s.seller_id, s.seller_name, s.city, s.rating;

-- Left Outer Join Scenario 2: Customers who have registered but never placed an order
SELECT 
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.email,
    c.registration_date,
    o.order_id
FROM Customer c
LEFT JOIN Orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL;

-- ==============================================================================
-- 6. RIGHT OUTER JOIN
-- Scenario: Find products that have never been added to any order (stagnant catalog items)
-- ==============================================================================
SELECT 
    oi.order_id,
    p.product_id,
    p.product_name,
    p.price,
    p.stock_quantity
FROM Order_Item oi
RIGHT JOIN Product p ON oi.product_id = p.product_id
WHERE oi.order_id IS NULL;

-- ==============================================================================
-- 7. FULL OUTER JOIN EMULATION (MySQL does not have FULL OUTER JOIN keyword)
-- Scenario: Retrieve all sellers and all products regardless of whether a seller
-- has products or a product is associated with a valid seller.
-- Emulated via LEFT JOIN UNION RIGHT JOIN.
-- ==============================================================================
SELECT 
    s.seller_name,
    s.city AS seller_city,
    p.product_name,
    p.price
FROM Seller s
LEFT JOIN Product p ON s.seller_id = p.seller_id

UNION

SELECT 
    s.seller_name,
    s.city AS seller_city,
    p.product_name,
    p.price
FROM Seller s
RIGHT JOIN Product p ON s.seller_id = p.seller_id;
