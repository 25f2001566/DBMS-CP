-- ==============================================================================
-- SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
-- File: 11_roles_and_multivendor.sql   (PHASE 1 - run AFTER 01..10)
-- Description: Adds login/roles, vendor approval, per-vendor item fulfilment,
--              delivery address on orders, and a cart-based checkout procedure.
-- Target Database: MySQL 8.0+
-- Syllabus link: Practical 2 (ALTER / constraints), Practical 5 (cursor),
--                Practical 6 (procedure + transaction), Enhanced ER (generalization)
-- ==============================================================================

USE ecommerce_db;

-- ------------------------------------------------------------------------------
-- 1. VENDOR APPROVAL: allow a 'Pending' seller status (admin approves later)
--    ALTER TABLE ... DROP CHECK / ADD CONSTRAINT  (MySQL 8.0.16+)
-- ------------------------------------------------------------------------------
ALTER TABLE Seller DROP CHECK Seller_chk_3;
ALTER TABLE Seller
    ADD CONSTRAINT chk_seller_status CHECK (status IN ('Pending', 'Active', 'Inactive'));

-- ------------------------------------------------------------------------------
-- 2. APP_USER: one login table for all three roles.
--    Customer / Seller keep their profile data; App_User holds credentials.
--    (Generalization: App_User is the "login" supertype, role says which subtype.)
--    FKs use RESTRICT because MySQL forbids CASCADE/SET NULL on columns that are
--    also used inside a CHECK constraint.
-- ------------------------------------------------------------------------------
CREATE TABLE App_User (
    user_id       INT PRIMARY KEY AUTO_INCREMENT,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,              -- never plain text
    role          VARCHAR(10)  NOT NULL,
    customer_id   INT NULL UNIQUE,
    seller_id     INT NULL UNIQUE,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    TIMESTAMP NULL,

    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (seller_id)   REFERENCES Seller(seller_id)     ON DELETE RESTRICT ON UPDATE RESTRICT,

    CHECK (role IN ('customer', 'vendor', 'admin')),
    -- A customer login points to exactly one Customer, a vendor to one Seller, an admin to neither.
    CHECK (
        (role = 'customer' AND customer_id IS NOT NULL AND seller_id IS NULL) OR
        (role = 'vendor'   AND seller_id   IS NOT NULL AND customer_id IS NULL) OR
        (role = 'admin'    AND customer_id IS NULL     AND seller_id IS NULL)
    )
);

-- ------------------------------------------------------------------------------
-- 3. PRODUCT: soft delete flag (vendors "unlist" instead of destroying order history)
-- ------------------------------------------------------------------------------
ALTER TABLE Product ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- ------------------------------------------------------------------------------
-- 4. ORDER_ITEM: each line carries its OWN fulfilment status, so one order can
--    contain items from several vendors and each vendor ships only their items.
-- ------------------------------------------------------------------------------
ALTER TABLE Order_Item
    ADD COLUMN item_status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    ADD CONSTRAINT chk_item_status CHECK (item_status IN ('Pending', 'Shipped', 'Delivered', 'Cancelled'));

-- Back-fill existing rows from their parent order (DML with a join)
UPDATE Order_Item oi
JOIN Orders o ON o.order_id = oi.order_id
SET oi.item_status = CASE o.order_status
        WHEN 'Delivered' THEN 'Delivered'
        WHEN 'Shipped'   THEN 'Shipped'
        WHEN 'Cancelled' THEN 'Cancelled'
        ELSE 'Pending'
    END;

-- ------------------------------------------------------------------------------
-- 5. ORDERS: which saved address the order ships to
-- ------------------------------------------------------------------------------
ALTER TABLE Orders
    ADD COLUMN address_id INT NULL,
    ADD CONSTRAINT fk_orders_address FOREIGN KEY (address_id)
        REFERENCES Customer_Address(address_id) ON DELETE RESTRICT ON UPDATE CASCADE;

-- ------------------------------------------------------------------------------
-- 6. PROCEDURE: place_order_from_cart
--    One transaction turns a customer's whole cart (products from MANY vendors)
--    into ONE Orders row + many Order_Item rows.
--    Demonstrates: explicit cursor, row locking, transaction, handlers, OUT params.
--    Stock is reduced by trg_order_item_after_insert (not here).
-- ------------------------------------------------------------------------------
DELIMITER //

DROP PROCEDURE IF EXISTS place_order_from_cart//
CREATE PROCEDURE place_order_from_cart(
    IN  p_customer_id    INT,
    IN  p_address_id     INT,
    IN  p_payment_method VARCHAR(30),
    OUT p_order_id       INT,
    OUT p_status_code    INT,
    OUT p_status_message VARCHAR(255)
)
proc_cart: BEGIN
    DECLARE v_done        INT DEFAULT 0;
    DECLARE v_failed      INT DEFAULT 0;
    DECLARE v_items       INT DEFAULT 0;
    DECLARE v_cart_id     INT;
    DECLARE v_cust_status VARCHAR(20);
    DECLARE v_addr_owner  INT;

    DECLARE v_product_id  INT;
    DECLARE v_qty         INT;
    DECLARE v_name        VARCHAR(100);
    DECLARE v_price       DECIMAL(10,2);
    DECLARE v_disc        DECIMAL(5,2);
    DECLARE v_stock       INT;
    DECLARE v_prod_active BOOLEAN;
    DECLARE v_sel_status  VARCHAR(20);

    -- Cursor over the cart. FOR UPDATE OF p locks the Product rows we are about to
    -- change, so two customers cannot buy the last unit at the same time.
    DECLARE cur_cart CURSOR FOR
        SELECT ci.product_id, ci.quantity, p.product_name, p.price, p.discount_percent,
               p.stock_quantity, p.is_active, s.status
        FROM Cart_Item ci
        JOIN Product p ON p.product_id = ci.product_id
        JOIN Seller  s ON s.seller_id  = p.seller_id
        WHERE ci.cart_id = v_cart_id
        FOR UPDATE OF p;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_order_id = 0;
        SET p_status_code = 500;
        SET p_status_message = 'Database error: checkout rolled back, nothing was saved.';
    END;

    SET p_order_id = 0;

    -- ---- Validation that needs no locks ----
    SELECT status INTO v_cust_status FROM Customer WHERE customer_id = p_customer_id;
    IF v_cust_status IS NULL THEN
        SET p_status_code = 404; SET p_status_message = 'Customer not found.';
        LEAVE proc_cart;
    ELSEIF v_cust_status <> 'Active' THEN
        SET p_status_code = 403; SET p_status_message = 'Customer account is inactive.';
        LEAVE proc_cart;
    END IF;

    SELECT customer_id INTO v_addr_owner FROM Customer_Address WHERE address_id = p_address_id;
    IF v_addr_owner IS NULL OR v_addr_owner <> p_customer_id THEN
        SET p_status_code = 400; SET p_status_message = 'Please choose one of your own saved addresses.';
        LEAVE proc_cart;
    END IF;

    SELECT cart_id INTO v_cart_id FROM Cart WHERE customer_id = p_customer_id;
    IF v_cart_id IS NULL THEN
        SET p_status_code = 400; SET p_status_message = 'Your cart is empty.';
        LEAVE proc_cart;
    END IF;

    -- ---- Atomic part ----
    START TRANSACTION;

    INSERT INTO Orders (customer_id, order_date, total_amount, order_status, address_id)
    VALUES (p_customer_id, CURDATE(), 0.00, 'Pending', p_address_id);
    SET p_order_id = LAST_INSERT_ID();

    OPEN cur_cart;
    cart_loop: LOOP
        FETCH cur_cart INTO v_product_id, v_qty, v_name, v_price, v_disc,
                            v_stock, v_prod_active, v_sel_status;
        IF v_done = 1 THEN LEAVE cart_loop; END IF;

        SET v_items = v_items + 1;

        IF v_prod_active = FALSE OR v_sel_status <> 'Active' THEN
            SET v_failed = 1;
            SET p_status_message = CONCAT('"', v_name, '" is no longer available.');
            LEAVE cart_loop;
        END IF;

        IF v_stock < v_qty THEN
            SET v_failed = 1;
            SET p_status_message = CONCAT('Not enough stock for "', v_name, '" (only ', v_stock, ' left).');
            LEAVE cart_loop;
        END IF;

        -- price frozen at purchase time, discount applied via our stored function
        INSERT INTO Order_Item (order_id, product_id, quantity, unit_price)
        VALUES (p_order_id, v_product_id, v_qty, calculate_discounted_price(v_price, v_disc));
    END LOOP cart_loop;
    CLOSE cur_cart;

    IF v_items = 0 THEN
        ROLLBACK;
        SET p_order_id = 0; SET p_status_code = 400; SET p_status_message = 'Your cart is empty.';
        LEAVE proc_cart;
    END IF;

    IF v_failed = 1 THEN
        ROLLBACK;
        SET p_order_id = 0; SET p_status_code = 409;
        LEAVE proc_cart;   -- p_status_message already says why
    END IF;

    UPDATE Orders SET total_amount = calculate_order_subtotal(p_order_id) WHERE order_id = p_order_id;

    -- Simulated payment (no gateway): COD stays Pending, everything else is "Completed"
    INSERT INTO Payment (order_id, payment_date, payment_method, payment_status)
    VALUES (p_order_id,
            IF(p_payment_method = 'COD', NULL, CURDATE()),
            p_payment_method,
            IF(p_payment_method = 'COD', 'Pending', 'Completed'));

    DELETE FROM Cart_Item WHERE cart_id = v_cart_id;

    COMMIT;

    SET p_status_code = 200;
    SET p_status_message = CONCAT('Order #', p_order_id, ' placed successfully.');
END //

DELIMITER ;
