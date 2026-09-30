-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 05_subqueries.sql
-- Description: Single-Row, Multi-Row, Correlated Subqueries & DML Subqueries (Lab 4)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

-- ==============================================================================
-- 1. SINGLE-ROW SUBQUERIES (Returns exactly one row and one column)
-- ==============================================================================

-- Q1.1: Find the most expensive product in the marketplace catalog
SELECT product_id, product_name, price, stock_quantity
FROM Product
WHERE price = (
    SELECT MAX(price) 
    FROM Product
);

-- Q1.2: Find all products whose price is strictly above the marketplace average price
SELECT product_id, product_name, price,
       ROUND((SELECT AVG(price) FROM Product), 2) AS marketplace_avg_price
FROM Product
WHERE price > (
    SELECT AVG(price) 
    FROM Product
)
ORDER BY price DESC;

-- Q1.3: Find the customer who placed the single highest value order
SELECT customer_id, first_name, last_name, email
FROM Customer
WHERE customer_id = (
    SELECT customer_id 
    FROM Orders 
    ORDER BY total_amount DESC 
    LIMIT 1
);

-- ==============================================================================
-- 2. MULTIPLE-ROW SUBQUERIES (IN, NOT IN, ANY, ALL)
-- ==============================================================================

-- Q2.1: Subquery using IN: Find products sold by vendors situated in Tier-1 cities
SELECT product_id, product_name, price, seller_id
FROM Product
WHERE seller_id IN (
    SELECT seller_id 
    FROM Seller 
    WHERE city IN ('Pune', 'Mumbai', 'Bengaluru')
);

-- Q2.2: Subquery using NOT IN: Customers who have never placed an order
SELECT customer_id, first_name, last_name, email
FROM Customer
WHERE customer_id NOT IN (
    SELECT DISTINCT customer_id 
    FROM Orders
);

-- Q2.3: Subquery using > ANY (Greater than at least one element in the set)
-- Find products that cost more than ANY product sold by FashionHub (seller_id = 2)
SELECT product_id, product_name, price
FROM Product
WHERE price > ANY (
    SELECT price 
    FROM Product 
    WHERE seller_id = 2
);

-- Q2.4: Subquery using > ALL (Greater than every single element in the set)
-- Find products that cost more than ALL products sold by FashionHub (seller_id = 2)
SELECT product_id, product_name, price
FROM Product
WHERE price > ALL (
    SELECT price 
    FROM Product 
    WHERE seller_id = 2
);

-- ==============================================================================
-- 3. CORRELATED SUBQUERIES (Subquery references attributes from outer query)
-- ==============================================================================

-- Q3.1: Correlated subquery using EXISTS: Customers who have active orders
SELECT c.customer_id, c.first_name, c.last_name, c.email
FROM Customer c
WHERE EXISTS (
    SELECT 1 
    FROM Orders o 
    WHERE o.customer_id = c.customer_id
);

-- Q3.2: Correlated subquery using NOT EXISTS: Inactive customers with no order history
SELECT c.customer_id, c.first_name, c.last_name, c.city
FROM Customer c
WHERE NOT EXISTS (
    SELECT 1 
    FROM Orders o 
    WHERE o.customer_id = c.customer_id
);

-- Q3.3: Correlated subquery for Category Relative Pricing:
-- Find products priced higher than the average price OF THEIR OWN SPECIFIC CATEGORY
SELECT p1.product_id, p1.product_name, p1.category_id, p1.price
FROM Product p1
WHERE p1.price > (
    SELECT AVG(p2.price)
    FROM Product p2
    WHERE p2.category_id = p1.category_id
);

-- Q3.4: Correlated subquery: Vendors whose rating exceeds the platform average rating
SELECT s.seller_id, s.seller_name, s.rating
FROM Seller s
WHERE s.rating > (
    SELECT AVG(s2.rating)
    FROM Seller s2
);

-- ==============================================================================
-- 4. DML QUERIES CONTAINING SUBQUERIES (INSERT, UPDATE, DELETE with Subqueries)
-- ==============================================================================

-- Q4.1: INSERT INTO with Subquery: Populate an archived table of top-tier products
CREATE TABLE IF NOT EXISTS Top_Tier_Product (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(100),
    price DECIMAL(10,2)
);

DELETE FROM Top_Tier_Product;

INSERT INTO Top_Tier_Product (product_id, product_name, price)
SELECT product_id, product_name, price
FROM Product
WHERE price > (
    SELECT AVG(price) 
    FROM Product
);

SELECT * FROM Top_Tier_Product;

-- Q4.2: UPDATE with Subquery: Increase price of all products under 'Electronics' category
UPDATE Product
SET price = ROUND(price * 1.02, 2)
WHERE category_id = (
    SELECT category_id 
    FROM Category 
    WHERE category_name = 'Electronics'
);

-- Q4.3: DELETE with Subquery: Clean up cart items for products priced under Rs. 700
DELETE FROM Cart_Item
WHERE product_id IN (
    SELECT product_id 
    FROM Product 
    WHERE price < 700.00
);
