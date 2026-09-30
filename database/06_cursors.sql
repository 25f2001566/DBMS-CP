-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 06_cursors.sql
-- Description: MySQL Stored Cursors for Batch Processing & Data Reconciliation (Lab 5)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

DELIMITER //

-- ==============================================================================
-- 1. SIMPLE EXPLICIT CURSOR
-- Objective: Process product catalog one row at a time.
-- Demonstrates: DECLARE CURSOR, DECLARE CONTINUE HANDLER FOR NOT FOUND,
--               OPEN, FETCH, LOOP, CLOSE.
-- ==============================================================================
DROP PROCEDURE IF EXISTS process_all_products_cursor//
CREATE PROCEDURE process_all_products_cursor()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_id INT;
    DECLARE v_name VARCHAR(100);
    DECLARE v_price DECIMAL(10,2);
    DECLARE v_stock INT;

    -- 1. Declare cursor
    DECLARE cur_product CURSOR FOR 
        SELECT product_id, product_name, price, stock_quantity 
        FROM Product;

    -- 2. Handler for when cursor reaches the end of the result set
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    -- Create temporary table to collect cursor-processed stream
    CREATE TEMPORARY TABLE IF NOT EXISTS Temp_Cursor_Output (
        prod_id INT,
        prod_name VARCHAR(100),
        unit_price DECIMAL(10,2),
        stock_status VARCHAR(50)
    );
    TRUNCATE TABLE Temp_Cursor_Output;

    -- 3. Open cursor
    OPEN cur_product;

    read_loop: LOOP
        -- 4. Fetch row into local procedural variables
        FETCH cur_product INTO v_id, v_name, v_price, v_stock;

        IF done = 1 THEN
            LEAVE read_loop;
        END IF;

        -- Process each row individually
        INSERT INTO Temp_Cursor_Output VALUES (
            v_id, 
            v_name, 
            v_price, 
            IF(v_stock < 10, 'LOW STOCK ALERT', 'SUFFICIENT STOCK')
        );
    END LOOP;

    -- 5. Close cursor and free resources
    CLOSE cur_product;

    -- Return cursor results
    SELECT * FROM Temp_Cursor_Output;
END //

-- ==============================================================================
-- 2. PARAMETERIZED CURSOR STORED PROCEDURE
-- Objective: Cursor dynamically filtered by an input threshold.
-- Demonstrates: IN parameter passed into cursor WHERE clause.
-- ==============================================================================
DROP PROCEDURE IF EXISTS filter_products_by_min_price_cursor//
CREATE PROCEDURE filter_products_by_min_price_cursor(IN p_min_price DECIMAL(10,2))
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_id INT;
    DECLARE v_name VARCHAR(100);
    DECLARE v_price DECIMAL(10,2);

    -- Declare cursor using the input parameter
    DECLARE cur_filtered CURSOR FOR
        SELECT product_id, product_name, price
        FROM Product
        WHERE price >= p_min_price
        ORDER BY price ASC;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    CREATE TEMPORARY TABLE IF NOT EXISTS Temp_Param_Cursor (
        prod_id INT,
        prod_name VARCHAR(100),
        price DECIMAL(10,2)
    );
    TRUNCATE TABLE Temp_Param_Cursor;

    OPEN cur_filtered;

    fetch_loop: LOOP
        FETCH cur_filtered INTO v_id, v_name, v_price;
        IF done = 1 THEN
            LEAVE fetch_loop;
        END IF;

        INSERT INTO Temp_Param_Cursor VALUES (v_id, v_name, v_price);
    END LOOP;

    CLOSE cur_filtered;

    SELECT * FROM Temp_Param_Cursor;
END //

-- ==============================================================================
-- 3. CURSOR FOR MULTI-VENDOR PAYOUT CALCULATION & TABLE UPDATE
-- Objective: Loop through all vendors, calculate their total sales from Order_Item,
-- compute the platform commission and net vendor payout, and record it.
-- Demonstrates: Real-world business batch processing using cursors.
-- ==============================================================================
DROP PROCEDURE IF EXISTS calculate_vendor_payouts_cursor//
CREATE PROCEDURE calculate_vendor_payouts_cursor()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_seller_id INT;
    DECLARE v_comm_rate DECIMAL(4,2);
    DECLARE v_total_sales DECIMAL(10,2);
    DECLARE v_commission DECIMAL(10,2);
    DECLARE v_net_payout DECIMAL(10,2);

    -- Cursor iterating through all active vendors
    DECLARE cur_seller CURSOR FOR
        SELECT seller_id, commission_rate
        FROM Seller
        WHERE status = 'Active';

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN cur_seller;

    payout_loop: LOOP
        FETCH cur_seller INTO v_seller_id, v_comm_rate;
        IF done = 1 THEN
            LEAVE payout_loop;
        END IF;

        -- Aggregate total sales for this vendor from delivered orders
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0.00)
        INTO v_total_sales
        FROM Order_Item oi
        INNER JOIN Product p ON oi.product_id = p.product_id
        INNER JOIN Orders o ON oi.order_id = o.order_id
        WHERE p.seller_id = v_seller_id
          AND o.order_status <> 'Cancelled';

        -- Calculate commission and net payout
        SET v_commission = ROUND(v_total_sales * (v_comm_rate / 100), 2);
        SET v_net_payout = v_total_sales - v_commission;

        -- Record calculated payout
        INSERT INTO Vendor_Payout (seller_id, total_sales, commission_deducted, net_payout, payout_date)
        VALUES (v_seller_id, v_total_sales, v_commission, v_net_payout, CURDATE());
    END LOOP;

    CLOSE cur_seller;

    -- Return updated payout ledger
    SELECT 
        vp.payout_id,
        s.seller_name,
        vp.total_sales,
        vp.commission_deducted,
        vp.net_payout,
        vp.payout_date
    FROM Vendor_Payout vp
    INNER JOIN Seller s ON vp.seller_id = s.seller_id
    WHERE vp.payout_date = CURDATE();
END //

-- ==============================================================================
-- 4. CURSOR FOR CATALOG PRICE ADJUSTMENT (CURSOR WITH UPDATE)
-- Objective: Loop through products in a specified category and apply an inflation/promotional adjustment.
-- ==============================================================================
DROP PROCEDURE IF EXISTS update_category_prices_cursor//
CREATE PROCEDURE update_category_prices_cursor(
    IN p_category_id INT,
    IN p_adjustment_percentage DECIMAL(5,2)
)
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_id INT;
    DECLARE v_price DECIMAL(10,2);

    DECLARE cur_price_update CURSOR FOR
        SELECT product_id, price
        FROM Product
        WHERE category_id = p_category_id;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN cur_price_update;

    adj_loop: LOOP
        FETCH cur_price_update INTO v_id, v_price;
        IF done = 1 THEN
            LEAVE adj_loop;
        END IF;

        UPDATE Product
        SET price = ROUND(v_price * (1 + (p_adjustment_percentage / 100)), 2)
        WHERE product_id = v_id;
    END LOOP;

    CLOSE cur_price_update;

    SELECT product_id, product_name, price 
    FROM Product 
    WHERE category_id = p_category_id;
END //

DELIMITER ;
