-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 09_triggers.sql
-- Description: Database Triggers for Automation, Integrity & Auditing (Lab 7)
-- Target Database: MySQL 8.0+
-- Course: AI 2303 - Database Management Systems (VIT Pune)
-- ==============================================================================

USE ecommerce_db;

DELIMITER //

-- ==============================================================================
-- 1. BEFORE INSERT TRIGGER: DATA NORMALIZATION & VALIDATION
-- Objective: Ensure customer email is converted to lowercase before saving.
-- Table: Customer | Event: BEFORE INSERT | Timing: Row-Level
-- ==============================================================================
DROP TRIGGER IF EXISTS trg_customer_before_insert//
CREATE TRIGGER trg_customer_before_insert
BEFORE INSERT ON Customer
FOR EACH ROW
BEGIN
    -- Normalize email to lowercase
    SET NEW.email = LOWER(TRIM(NEW.email));

    -- Set default registration date if not supplied
    IF NEW.registration_date IS NULL THEN
        SET NEW.registration_date = CURDATE();
    END IF;
END //

-- ==============================================================================
-- 2. AFTER INSERT TRIGGER: AUTOMATIC INVENTORY DECREMENT
-- Objective: When an order line item is inserted, automatically deduct
--            ordered quantity from the vendor's product stock.
-- Table: Order_Item | Event: AFTER INSERT | Timing: Row-Level
-- ==============================================================================
DROP TRIGGER IF EXISTS trg_order_item_after_insert//
CREATE TRIGGER trg_order_item_after_insert
AFTER INSERT ON Order_Item
FOR EACH ROW
BEGIN
    UPDATE Product
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
END //

-- ==============================================================================
-- 3. BEFORE UPDATE TRIGGER: PREVENT NEGATIVE INVENTORY (BUSINESS INTEGRITY GUARD)
-- Objective: Throws a SQLSTATE error exception if an update would result in negative stock.
-- Table: Product | Event: BEFORE UPDATE | Timing: Row-Level
-- ==============================================================================
DROP TRIGGER IF EXISTS trg_product_before_update//
CREATE TRIGGER trg_product_before_update
BEFORE UPDATE ON Product
FOR EACH ROW
BEGIN
    IF NEW.stock_quantity < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Integrity Violation: Stock quantity cannot be negative.';
    END IF;
END //

-- ==============================================================================
-- 4. AFTER UPDATE TRIGGER: ORDER STATUS AUDIT LOGGING
-- Objective: When an order status changes (e.g. 'Processing' -> 'Delivered'),
--            automatically log the transition timestamp and states into Order_Audit_Log.
-- Table: Orders | Event: AFTER UPDATE | Timing: Row-Level
-- ==============================================================================
DROP TRIGGER IF EXISTS trg_orders_after_update_audit//
CREATE TRIGGER trg_orders_after_update_audit
AFTER UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF OLD.order_status <> NEW.order_status THEN
        INSERT INTO Order_Audit_Log (order_id, old_status, new_status, action_type)
        VALUES (NEW.order_id, OLD.order_status, NEW.order_status, 'STATUS_CHANGE');
    END IF;
END //

-- ==============================================================================
-- 5. BEFORE DELETE TRIGGER: PREVENT DELETION OF PRODUCTS WITH ACTIVE ORDERS
-- Objective: Protects relational consistency from accidental hard-deletions.
-- Table: Product | Event: BEFORE DELETE | Timing: Row-Level
-- ==============================================================================
DROP TRIGGER IF EXISTS trg_product_before_delete//
CREATE TRIGGER trg_product_before_delete
BEFORE DELETE ON Product
FOR EACH ROW
BEGIN
    DECLARE v_active_orders INT DEFAULT 0;

    SELECT COUNT(*) INTO v_active_orders
    FROM Order_Item oi
    INNER JOIN Orders o ON oi.order_id = o.order_id
    WHERE oi.product_id = OLD.product_id
      AND o.order_status IN ('Pending', 'Processing', 'Shipped');

    IF v_active_orders > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Deletion Denied: Product is associated with active, undelivered orders.';
    END IF;
END //

DELIMITER ;

-- Verification: View all active triggers
SHOW TRIGGERS FROM ecommerce_db;
