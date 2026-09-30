-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 03_queries_dql.sql
-- Description: DQL & Business Queries Demonstrating Syllabus Concepts (Lab 3)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

-- ==============================================================================
-- 1. CONDITIONAL OPERATORS (=, <>, <, >, <=, >=)
-- ==============================================================================

-- Q1.1: Retrieve all premium products costing more than Rs. 5,000
SELECT product_id, product_name, price, stock_quantity
FROM Product
WHERE price > 5000.00;

-- Q1.2: Retrieve affordable products costing less than Rs. 2,000
SELECT product_id, product_name, price, stock_quantity
FROM Product
WHERE price < 2000.00;

-- Q1.3: Retrieve products with price at least Rs. 1,000
SELECT product_id, product_name, price
FROM Product
WHERE price >= 1000.00;

-- Q1.4: Retrieve products whose price is not exactly Rs. 3,500
SELECT product_id, product_name, price
FROM Product
WHERE price <> 3500.00;

-- ==============================================================================
-- 2. LOGICAL OPERATORS (AND, OR, NOT)
-- ==============================================================================

-- Q2.1: Products priced over Rs. 1,000 having healthy stock (> 30 units)
SELECT product_id, product_name, price, stock_quantity
FROM Product
WHERE price > 1000.00 AND stock_quantity > 30;

-- Q2.2: Products belonging to either Electronics (category 1) or Books (category 4)
SELECT product_id, product_name, category_id, price
FROM Product
WHERE category_id = 1 OR category_id = 4;

-- Q2.3: Products not belonging to Electronics category
SELECT product_id, product_name, category_id
FROM Product
WHERE NOT (category_id = 1);

-- ==============================================================================
-- 3. PATTERN MATCHING (LIKE, NOT LIKE)
-- ==============================================================================

-- Q3.1: Customers whose first name starts with 'A'
SELECT customer_id, first_name, last_name, city
FROM Customer
WHERE first_name LIKE 'A%';

-- Q3.2: Products containing 'book' anywhere in their name (case-insensitive in MySQL)
SELECT product_id, product_name, price
FROM Product
WHERE product_name LIKE '%book%';

-- Q3.3: Customers registered with Gmail accounts
SELECT customer_id, first_name, email
FROM Customer
WHERE email LIKE '%@gmail.com';

-- Q3.4: Products that do NOT contain the word 'Pro' in their name
SELECT product_id, product_name
FROM Product
WHERE product_name NOT LIKE '%Pro%';

-- ==============================================================================
-- 4. MEMBERSHIP & RANGE OPERATORS (IN, NOT IN, BETWEEN...AND)
-- ==============================================================================

-- Q4.1: Products in Electronics, Home Appliances, or Books
SELECT product_id, product_name, category_id, price
FROM Product
WHERE category_id IN (1, 3, 4);

-- Q4.2: Products not sold by Seller 1 or Seller 2
SELECT product_id, product_name, seller_id, price
FROM Product
WHERE seller_id NOT IN (1, 2);

-- Q4.3: Products priced between Rs. 1,000 and Rs. 5,000 inclusive
SELECT product_id, product_name, price
FROM Product
WHERE price BETWEEN 1000.00 AND 5000.00;

-- ==============================================================================
-- 5. NULL CHECKING (IS NULL, IS NOT NULL)
-- ==============================================================================

-- Q5.1: Orders where payment date is NULL (e.g. pending COD orders)
SELECT payment_id, order_id, payment_method, payment_status
FROM Payment
WHERE payment_date IS NULL;

-- Q5.2: Payments that have a verified payment date
SELECT payment_id, order_id, payment_date, payment_method, payment_status
FROM Payment
WHERE payment_date IS NOT NULL;

-- ==============================================================================
-- 6. SORTING (ORDER BY ASC/DESC)
-- ==============================================================================

-- Q6.1: Products sorted by price ascending (cheapest first)
SELECT product_id, product_name, price
FROM Product
ORDER BY price ASC;

-- Q6.2: Products sorted by rating descending (highest rated first)
SELECT product_id, product_name, product_rating, price
FROM Product
ORDER BY product_rating DESC, price ASC;

-- ==============================================================================
-- 7. GROUPING & AGGREGATE FUNCTIONS (COUNT, SUM, AVG, MIN, MAX, HAVING)
-- ==============================================================================

-- Q7.1: Overall platform inventory summary
SELECT 
    COUNT(*) AS total_products,
    SUM(price * stock_quantity) AS total_inventory_value,
    AVG(price) AS average_price,
    MIN(price) AS lowest_price,
    MAX(price) AS highest_price
FROM Product;

-- Q7.2: Total products and average price per category
SELECT 
    category_id, 
    COUNT(*) AS product_count, 
    ROUND(AVG(price), 2) AS avg_category_price
FROM Product
GROUP BY category_id;

-- Q7.3: Total sales generated per customer
SELECT 
    customer_id, 
    COUNT(order_id) AS total_orders, 
    SUM(total_amount) AS total_spent
FROM Orders
GROUP BY customer_id;

-- Q7.4: High-value customers who spent more than Rs. 5,000 (HAVING clause)
SELECT 
    customer_id, 
    COUNT(order_id) AS orders_placed, 
    SUM(total_amount) AS total_spent
FROM Orders
GROUP BY customer_id
HAVING SUM(total_amount) > 5000.00;

-- Q7.5: Sellers whose catalog has an average price greater than Rs. 4,000
SELECT 
    seller_id, 
    COUNT(product_id) AS items_listed, 
    ROUND(AVG(price), 2) AS avg_product_price
FROM Product
GROUP BY seller_id
HAVING AVG(price) > 4000.00;

-- ==============================================================================
-- 8. SET OPERATIONS (UNION, UNION ALL, INTERSECT & MINUS in MySQL)
-- ==============================================================================

-- Q8.1: UNION (Distinct cities where customers or sellers reside)
SELECT city FROM Customer WHERE city IS NOT NULL
UNION
SELECT city FROM Seller WHERE city IS NOT NULL;

-- Q8.2: UNION ALL (All customer and seller cities, preserving duplicates)
SELECT city, 'Customer' AS EntityType FROM Customer WHERE city IS NOT NULL
UNION ALL
SELECT city, 'Seller' AS EntityType FROM Seller WHERE city IS NOT NULL;

-- Q8.3: INTERSECT Equivalent in MySQL (Cities having BOTH customers and sellers)
-- MySQL 8.0.31+ supports INTERSECT natively; also works via INNER JOIN for compatibility
SELECT DISTINCT c.city
FROM Customer c
INNER JOIN Seller s ON c.city = s.city;

-- Q8.4: MINUS / EXCEPT Equivalent in MySQL (Cities having customers but NO sellers)
SELECT DISTINCT c.city
FROM Customer c
WHERE c.city NOT IN (
    SELECT s.city 
    FROM Seller s 
    WHERE s.city IS NOT NULL
);

-- ==============================================================================
-- 9. SINGLE-ROW FUNCTIONS (Date, Time, String, Numeric, NULL Handling)
-- ==============================================================================

-- Q9.1: Date & Time functions
SELECT 
    order_id,
    order_date,
    CURDATE() AS current_date_val,
    YEAR(order_date) AS order_year,
    MONTHNAME(order_date) AS order_month_name,
    DAYOFWEEK(order_date) AS order_weekday,
    DATEDIFF(CURDATE(), order_date) AS days_elapsed,
    DATE_FORMAT(order_date, '%d-%M-%Y') AS formatted_order_date
FROM Orders;

-- Q9.2: String manipulation functions
SELECT 
    customer_id,
    CONCAT(UPPER(first_name), ' ', UPPER(last_name)) AS full_name_upper,
    LOWER(email) AS normalized_email,
    LENGTH(first_name) AS name_char_count,
    LEFT(phone, 5) AS phone_prefix
FROM Customer;

-- Q9.3: Numeric functions & NULL handling (ROUND, CEIL, FLOOR, COALESCE)
SELECT 
    product_id,
    product_name,
    price,
    discount_percent,
    ROUND(price * (1 - discount_percent / 100), 2) AS final_discounted_price,
    CEIL(price * 0.90) AS ceiling_price,
    FLOOR(price * 0.90) AS floor_price
FROM Product;

SELECT 
    p.payment_id,
    p.order_id,
    COALESCE(DATE_FORMAT(p.payment_date, '%Y-%m-%d'), 'Awaiting Delivery') AS payment_status_detail,
    p.payment_method
FROM Payment p;
