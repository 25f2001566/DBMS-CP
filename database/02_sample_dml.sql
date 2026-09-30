-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 02_sample_dml.sql
-- Description: Realistic Sample Data Insertion (DML)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

-- Clear previous test data in child-to-parent order to respect foreign keys
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE Order_Audit_Log;
TRUNCATE TABLE Vendor_Payout;
TRUNCATE TABLE Cart_Item;
TRUNCATE TABLE Cart;
TRUNCATE TABLE Payment;
TRUNCATE TABLE Order_Item;
TRUNCATE TABLE Orders;
TRUNCATE TABLE Customer_Address;
TRUNCATE TABLE Product;
TRUNCATE TABLE Category;
TRUNCATE TABLE Seller;
TRUNCATE TABLE Customer;
TRUNCATE TABLE Price_Range;
SET FOREIGN_KEY_CHECKS = 1;

-- ------------------------------------------------------------------------------
-- 1. POPULATE CUSTOMERS
-- ------------------------------------------------------------------------------
INSERT INTO Customer (customer_id, first_name, last_name, email, phone, registration_date, city, status) VALUES
(1, 'Aarav', 'Sharma', 'aarav.sharma@gmail.com', '9876543210', '2025-01-10', 'Pune', 'Active'),
(2, 'Riya', 'Patil', 'riya.patil@gmail.com', '9876543211', '2025-02-15', 'Mumbai', 'Active'),
(3, 'Aditya', 'Deshmukh', 'aditya.d@gmail.com', '9876543212', '2025-03-20', 'Nagpur', 'Active'),
(4, 'Sneha', 'Joshi', 'sneha.joshi@gmail.com', '9876543213', '2025-04-12', 'Nashik', 'Active'),
(5, 'Rahul', 'Kulkarni', 'rahul.k@gmail.com', '9876543214', '2025-05-05', 'Pune', 'Inactive'),
(6, 'Priya', 'Shinde', 'priya.s@gmail.com', '9876543215', '2025-06-18', 'Aurangabad', 'Active'),
(7, 'Karan', 'Jadhav', 'karan.j@gmail.com', '9876543216', '2025-07-22', 'Kolhapur', 'Active'),
(8, 'Neha', 'More', 'neha.more@gmail.com', '9876543217', '2025-08-01', 'Pune', 'Active'),
(9, 'Vikram', 'Malhotra', 'vikram.m@gmail.com', '9876543218', '2025-08-15', 'Mumbai', 'Active'),
(10, 'Ananya', 'Iyer', 'ananya.iyer@gmail.com', '9876543219', '2025-09-01', 'Bengaluru', 'Active');

-- ------------------------------------------------------------------------------
-- 2. POPULATE SELLERS / VENDORS
-- ------------------------------------------------------------------------------
INSERT INTO Seller (seller_id, seller_name, email, phone, city, rating, commission_rate, registration_date, status) VALUES
(1, 'TechWorld Electronics', 'contact@techworld.com', '9000000001', 'Pune', 4.6, 8.00, '2024-01-10', 'Active'),
(2, 'FashionHub Trends', 'support@fashionhub.com', '9000000002', 'Mumbai', 4.2, 12.00, '2024-02-15', 'Active'),
(3, 'HomeNeeds Appliances', 'sales@homeneeds.com', '9000000003', 'Nagpur', 4.5, 10.00, '2024-03-20', 'Active'),
(4, 'BookStore Central', 'orders@bookstore.com', '9000000004', 'Pune', 4.8, 5.00, '2024-04-10', 'Active'),
(5, 'SportsZone Arena', 'info@sportszone.com', '9000000005', 'Nashik', 3.9, 10.00, '2024-05-12', 'Active'),
(6, 'Gourmet Organic Goods', 'hello@gourmetgoods.com', '9000000006', 'Kolhapur', 4.7, 7.50, '2024-06-01', 'Active');

-- ------------------------------------------------------------------------------
-- 3. POPULATE CATEGORIES
-- ------------------------------------------------------------------------------
INSERT INTO Category (category_id, category_name, description) VALUES
(1, 'Electronics', 'Laptops, mobile devices, audio and high-tech computer peripherals'),
(2, 'Clothing & Fashion', 'Men, women, and kids apparel, streetwear and formal attire'),
(3, 'Home Appliances', 'Kitchen and living space electrical home automation appliances'),
(4, 'Books & Media', 'Academic engineering textbooks, fiction and programming guides'),
(5, 'Sports & Fitness', 'Outdoor sports gear, athletic equipment, and fitness accessories'),
(6, 'Gourmet & Groceries', 'Organic farm produce, packaged snacks, and premium beverages');

-- ------------------------------------------------------------------------------
-- 4. POPULATE PRODUCTS
-- Includes varying prices, discounts, and low-stock items (< 15) for testing alerts
-- ------------------------------------------------------------------------------
INSERT INTO Product (product_id, product_name, seller_id, category_id, price, stock_quantity, product_rating, added_date, discount_percent) VALUES
(1, 'ThinkPad Pro Laptop 16GB', 1, 1, 75000.00, 18, 4.7, '2025-01-15', 10.00),
(2, 'Ergonomic Wireless Mouse', 1, 1, 1250.00, 85, 4.5, '2025-02-10', 5.00),
(3, 'RGB Mechanical Keyboard', 1, 1, 3500.00, 42, 4.6, '2025-03-05', 8.00),
(4, 'Ultra 5G Smartphone 128GB', 1, 1, 45000.00, 24, 4.4, '2025-03-20', 12.00),
(5, 'Noise-Cancelling Headphones', 1, 1, 6500.00, 8, 4.8, '2025-04-10', 15.00), -- Low Stock (8)

(6, 'Cotton Crewneck T-Shirt', 2, 2, 850.00, 120, 4.2, '2025-01-20', 15.00),
(7, 'Slim-Fit Stretch Denim Jeans', 2, 2, 1850.00, 65, 4.1, '2025-02-25', 10.00),
(8, 'Windproof Winter Jacket', 2, 2, 3200.00, 32, 4.3, '2025-03-15', 20.00),

(9, 'Multi-Speed Mixer Grinder 750W', 3, 3, 4500.00, 28, 4.5, '2025-01-30', 7.00),
(10, 'Digital Rapid Air Fryer 4.2L', 3, 3, 6800.00, 6, 4.6, '2025-04-01', 10.00), -- Low Stock (6)
(11, 'Smart Microwave Oven 25L', 3, 3, 11500.00, 14, 4.3, '2025-04-15', 12.00),

(12, 'DBMS Concepts (Silberschatz)', 4, 4, 950.00, 50, 4.8, '2025-02-01', 5.00),
(13, 'Python for Data Analysis Guide', 4, 4, 750.00, 65, 4.7, '2025-02-15', 5.00),
(14, 'Algorithms & Data Structures in C++', 4, 4, 1100.00, 4, 4.9, '2025-03-10', 0.00), -- Low Stock (4)

(15, 'FIFA Match Regulation Football', 5, 5, 1500.00, 38, 4.4, '2025-03-01', 10.00),
(16, 'Adjustable Dumbbell Set 20KG', 5, 5, 4200.00, 19, 4.5, '2025-03-25', 8.00),

(17, 'Organic Himalayan Honey 500g', 6, 6, 550.00, 90, 4.7, '2025-06-05', 5.00),
(18, 'Single-Origin Coffee Beans 250g', 6, 6, 680.00, 5, 4.6, '2025-06-12', 0.00); -- Low Stock (5)

-- ------------------------------------------------------------------------------
-- 5. POPULATE CUSTOMER ADDRESSES
-- ------------------------------------------------------------------------------
INSERT INTO Customer_Address (address_id, customer_id, address_line, city, state, pincode, is_default) VALUES
(1, 1, 'Flat 402, Shivajinagar FC Road', 'Pune', 'Maharashtra', '411004', 1),
(2, 2, 'B-12, Green Palms, Andheri West', 'Mumbai', 'Maharashtra', '400058', 1),
(3, 3, 'Plot 88, West High Court Rd, Dharampeth', 'Nagpur', 'Maharashtra', '440010', 1),
(4, 4, '14 Anand Nagar, College Road', 'Nashik', 'Maharashtra', '422005', 1),
(5, 5, 'Bungalow 7, Mayur Colony, Kothrud', 'Pune', 'Maharashtra', '411038', 1),
(6, 6, 'Shop 3, CIDCO Sector N-5', 'Aurangabad', 'Maharashtra', '431001', 1),
(7, 7, '210/A, 5th Lane, Rajarampuri', 'Kolhapur', 'Maharashtra', '416008', 1),
(8, 8, 'Tower 3, Highmont, Baner-Pashan Link Rd', 'Pune', 'Maharashtra', '411045', 1),
(9, 9, 'Flat 101, Sea Crest, Bandra Bandstand', 'Mumbai', 'Maharashtra', '400050', 1),
(10, 10, '12th Main, 4th Block, Koramangala', 'Bengaluru', 'Karnataka', '560034', 1);

-- ------------------------------------------------------------------------------
-- 6. POPULATE PRICE RANGE (For Non-Equijoin Lab Requirement)
-- ------------------------------------------------------------------------------
INSERT INTO Price_Range (range_id, range_name, minimum_price, maximum_price) VALUES
(1, 'Budget Economy', 0.00, 1500.00),
(2, 'Mid-Range Value', 1500.01, 7000.00),
(3, 'Premium High-Tier', 7000.01, 30000.00),
(4, 'Luxury Flagship', 30000.01, 100000.00);

-- ------------------------------------------------------------------------------
-- 7. POPULATE ORDERS
-- Multi-vendor order history across dates and lifecycle states
-- ------------------------------------------------------------------------------
INSERT INTO Orders (order_id, customer_id, order_date, total_amount, order_status) VALUES
(1, 1, '2025-06-01', 76250.00, 'Delivered'),
(2, 2, '2025-06-05', 1850.00, 'Delivered'),
(3, 3, '2025-06-10', 45000.00, 'Shipped'),
(4, 4, '2025-06-15', 4500.00, 'Processing'),
(5, 1, '2025-07-01', 3500.00, 'Delivered'),
(6, 6, '2025-07-05', 6800.00, 'Pending'),
(7, 7, '2025-07-10', 1500.00, 'Delivered'),
(8, 8, '2025-07-15', 950.00, 'Cancelled'),
(9, 9, '2025-07-20', 13000.00, 'Delivered'),
(10, 10, '2025-07-25', 1230.00, 'Processing');

-- ------------------------------------------------------------------------------
-- 8. POPULATE ORDER ITEMS
-- Demonstrating multi-vendor orders (e.g. Order 1 contains items from TechWorld,
-- Order 9 contains HomeNeeds & Food items)
-- ------------------------------------------------------------------------------
INSERT INTO Order_Item (order_item_id, order_id, product_id, quantity, unit_price) VALUES
-- Order 1: Laptop + Mouse
(1, 1, 1, 1, 75000.00),
(2, 1, 2, 1, 1250.00),

-- Order 2: Denim Jeans
(3, 2, 7, 1, 1850.00),

-- Order 3: 5G Smartphone
(4, 3, 4, 1, 45000.00),

-- Order 4: Mixer Grinder
(5, 4, 9, 1, 4500.00),

-- Order 5: Mechanical Keyboard
(6, 5, 3, 1, 3500.00),

-- Order 6: Air Fryer
(7, 6, 10, 1, 6800.00),

-- Order 7: Football
(8, 7, 15, 1, 1500.00),

-- Order 8: DBMS Book (Cancelled)
(9, 8, 12, 1, 950.00),

-- Order 9: Microwave + Dumbbell Set (Multi-vendor order: Seller 3 & Seller 5)
(10, 9, 11, 1, 11500.00),
(11, 9, 16, 1, 1500.00),

-- Order 10: Honey + Single Origin Coffee (Seller 6)
(12, 10, 17, 1, 550.00),
(13, 10, 18, 1, 680.00);

-- ------------------------------------------------------------------------------
-- 9. POPULATE PAYMENTS
-- ------------------------------------------------------------------------------
INSERT INTO Payment (payment_id, order_id, payment_date, payment_method, payment_status) VALUES
(1, 1, '2025-06-01', 'Credit Card', 'Completed'),
(2, 2, '2025-06-05', 'UPI', 'Completed'),
(3, 3, '2025-06-10', 'Debit Card', 'Completed'),
(4, 4, '2025-06-15', 'UPI', 'Completed'),
(5, 5, '2025-07-01', 'Credit Card', 'Completed'),
(6, 6, NULL, 'COD', 'Pending'),
(7, 7, '2025-07-10', 'UPI', 'Completed'),
(8, 8, '2025-07-15', 'Credit Card', 'Refunded'),
(9, 9, '2025-07-20', 'Net Banking', 'Completed'),
(10, 10, '2025-07-25', 'UPI', 'Completed');

-- ------------------------------------------------------------------------------
-- 10. POPULATE ACTIVE CARTS AND CART ITEMS
-- ------------------------------------------------------------------------------
INSERT INTO Cart (cart_id, customer_id, created_date) VALUES
(1, 1, '2025-08-01'),
(2, 2, '2025-08-05'),
(3, 3, '2025-08-10'),
(4, 4, '2025-08-15'),
(5, 5, '2025-08-18'),
(6, 6, '2025-08-20'),
(7, 7, '2025-08-22'),
(8, 8, '2025-08-25');

INSERT INTO Cart_Item (cart_item_id, cart_id, product_id, quantity) VALUES
(1, 1, 3, 1),  -- Keyboard
(2, 1, 5, 1),  -- Headphones
(3, 2, 1, 1),  -- Laptop
(4, 3, 12, 2), -- 2 DBMS Books
(5, 4, 15, 1), -- Football
(6, 5, 8, 1),  -- Jacket
(7, 6, 2, 3),  -- 3 Mice
(8, 7, 9, 1);  -- Mixer

-- Verification count
SELECT 'Customers' AS Entity, COUNT(*) AS TotalRecords FROM Customer
UNION ALL
SELECT 'Sellers', COUNT(*) FROM Seller
UNION ALL
SELECT 'Categories', COUNT(*) FROM Category
UNION ALL
SELECT 'Products', COUNT(*) FROM Product
UNION ALL
SELECT 'Orders', COUNT(*) FROM Orders
UNION ALL
SELECT 'Order_Items', COUNT(*) FROM Order_Item
UNION ALL
SELECT 'Payments', COUNT(*) FROM Payment;
