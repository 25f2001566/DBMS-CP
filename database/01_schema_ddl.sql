-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 01_schema_ddl.sql
-- Description: Complete Database Creation & DDL Schema with Integrity Constraints
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

DROP DATABASE IF EXISTS ecommerce_db;
CREATE DATABASE ecommerce_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecommerce_db;

-- ------------------------------------------------------------------------------
-- 1. CUSTOMER TABLE
-- Represents customers registered on the platform.
-- Demonstrates: PRIMARY KEY, AUTO_INCREMENT, NOT NULL, UNIQUE, CHECK constraints
-- ------------------------------------------------------------------------------
CREATE TABLE Customer (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15) UNIQUE,
    registration_date DATE NOT NULL,
    city VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Active',
    CHECK (status IN ('Active', 'Inactive'))
);

-- ------------------------------------------------------------------------------
-- 2. SELLER / VENDOR TABLE
-- Represents multi-vendor store partners selling on the marketplace.
-- Demonstrates: Range CHECK constraints, DEFAULTs, UNIQUE business identifiers
-- ------------------------------------------------------------------------------
CREATE TABLE Seller (
    seller_id INT PRIMARY KEY AUTO_INCREMENT,
    seller_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(15) UNIQUE,
    city VARCHAR(50),
    rating DECIMAL(2,1) DEFAULT 0.0,
    commission_rate DECIMAL(4,2) DEFAULT 10.00, -- Multi-vendor platform commission (e.g. 10%)
    registration_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Active',
    CHECK (rating BETWEEN 0.0 AND 5.0),
    CHECK (commission_rate BETWEEN 0.00 AND 100.00),
    CHECK (status IN ('Active', 'Inactive'))
);

-- ------------------------------------------------------------------------------
-- 3. CATEGORY TABLE
-- Hierarchical categorization for marketplace products.
-- ------------------------------------------------------------------------------
CREATE TABLE Category (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- ------------------------------------------------------------------------------
-- 4. PRODUCT TABLE
-- Products listed by independent sellers under specific categories.
-- Demonstrates: Multiple FOREIGN KEY relationships, business validation checks
-- ------------------------------------------------------------------------------
CREATE TABLE Product (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100) NOT NULL,
    seller_id INT NOT NULL,
    category_id INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    product_rating DECIMAL(2,1) DEFAULT 0.0,
    added_date DATE NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0.00,
    
    FOREIGN KEY (seller_id) REFERENCES Seller(seller_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (category_id) REFERENCES Category(category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    
    CHECK (price > 0),
    CHECK (stock_quantity >= 0),
    CHECK (product_rating BETWEEN 0.0 AND 5.0),
    CHECK (discount_percent BETWEEN 0.00 AND 100.00)
);

-- ------------------------------------------------------------------------------
-- 5. CUSTOMER ADDRESS TABLE
-- Normalization: 1:M relationship with Customer to support multiple delivery locations
-- ------------------------------------------------------------------------------
CREATE TABLE Customer_Address (
    address_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    address_line VARCHAR(255) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ------------------------------------------------------------------------------
-- 6. ORDERS TABLE
-- Master order records placed by customers.
-- Demonstrates: Order lifecycle states, FK relationship, CHECK constraints
-- ------------------------------------------------------------------------------
CREATE TABLE Orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    order_status VARCHAR(30) DEFAULT 'Pending',
    
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    
    CHECK (total_amount >= 0),
    CHECK (order_status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'))
);

-- ------------------------------------------------------------------------------
-- 7. ORDER ITEM TABLE
-- Associative entity resolving M:N between Orders and Products in multi-vendor setup.
-- Captures point-in-time unit_price and quantity ordered.
-- ------------------------------------------------------------------------------
CREATE TABLE Order_Item (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    
    CHECK (quantity > 0),
    CHECK (unit_price > 0)
);

-- ------------------------------------------------------------------------------
-- 8. PAYMENT TABLE
-- 1:1 relationship with Orders for financial settlement and tracking.
-- ------------------------------------------------------------------------------
CREATE TABLE Payment (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL UNIQUE,
    payment_date DATE,
    payment_method VARCHAR(30) NOT NULL,
    payment_status VARCHAR(30) DEFAULT 'Pending',
    
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE ON UPDATE CASCADE,
    
    CHECK (payment_method IN ('UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'COD')),
    CHECK (payment_status IN ('Pending', 'Completed', 'Failed', 'Refunded'))
);

-- ------------------------------------------------------------------------------
-- 9. CART TABLE
-- Active cart per registered customer (1:1 with Customer).
-- ------------------------------------------------------------------------------
CREATE TABLE Cart (
    cart_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL UNIQUE,
    created_date DATE NOT NULL,
    
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ------------------------------------------------------------------------------
-- 10. CART ITEM TABLE
-- Individual products buffered in shopping carts prior to checkout.
-- ------------------------------------------------------------------------------
CREATE TABLE Cart_Item (
    cart_item_id INT PRIMARY KEY AUTO_INCREMENT,
    cart_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    
    FOREIGN KEY (cart_id) REFERENCES Cart(cart_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Product(product_id) ON DELETE CASCADE ON UPDATE CASCADE,
    
    CHECK (quantity > 0)
);

-- ------------------------------------------------------------------------------
-- 11. PRICE RANGE TABLE
-- Auxiliary reference entity specifically satisfying syllabus requirements
-- for non-equijoin queries (categorizing items without an exact FK equality).
-- ------------------------------------------------------------------------------
CREATE TABLE Price_Range (
    range_id INT PRIMARY KEY,
    range_name VARCHAR(30) NOT NULL,
    minimum_price DECIMAL(10,2) NOT NULL,
    maximum_price DECIMAL(10,2) NOT NULL
);

-- ------------------------------------------------------------------------------
-- 12. ORDER AUDIT LOG TABLE
-- Trigger-driven automated tracking for order status transitions.
-- Demonstrates: Audit trail, database automation, temporal logging
-- ------------------------------------------------------------------------------
CREATE TABLE Order_Audit_Log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_type VARCHAR(20) NOT NULL
);

-- ------------------------------------------------------------------------------
-- 13. VENDOR PAYOUT TABLE
-- Stored procedure and cursor target table for multi-vendor revenue reconciliation.
-- ------------------------------------------------------------------------------
CREATE TABLE Vendor_Payout (
    payout_id INT PRIMARY KEY AUTO_INCREMENT,
    seller_id INT NOT NULL,
    total_sales DECIMAL(10,2) DEFAULT 0.00,
    commission_deducted DECIMAL(10,2) DEFAULT 0.00,
    net_payout DECIMAL(10,2) DEFAULT 0.00,
    payout_date DATE NOT NULL,
    
    FOREIGN KEY (seller_id) REFERENCES Seller(seller_id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Verification: List all created tables
SHOW TABLES;
