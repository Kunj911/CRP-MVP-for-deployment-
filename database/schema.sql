-- =========================================================
-- LIVE-TRACE EXPORT DASHBOARD DATABASE SCHEMA
-- Database: MySQL
-- =========================================================

CREATE DATABASE IF NOT EXISTS live_trace_dashboard;

USE live_trace_dashboard;

-- =========================================================
-- 1. CUSTOMERS TABLE
-- =========================================================

CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,

    company_name VARCHAR(200) NOT NULL,
    contact_person VARCHAR(100),

    email VARCHAR(150),
    phone VARCHAR(20),

    country VARCHAR(100),
    timezone VARCHAR(100),

    address TEXT,

    storage_quota_mb INT NOT NULL DEFAULT 1000,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 2. USERS TABLE
-- =========================================================

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,

    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20),

    password_hash VARCHAR(255) NOT NULL,

    role ENUM(
        'SUPER_ADMIN',
        'ADMIN',
        'WAREHOUSE',
        'QA',
        'DOCUMENTATION',
        'CUSTOMER'
    ) NOT NULL,

    customer_id INT NULL,

    is_active BOOLEAN DEFAULT TRUE,

    mfa_enabled BOOLEAN DEFAULT FALSE,
    totp_secret VARCHAR(255) NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

-- =========================================================
-- 3. ORDERS TABLE
-- =========================================================

CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,

    order_code VARCHAR(50) UNIQUE NOT NULL,

    customer_id INT NOT NULL,

    product_name VARCHAR(200) NOT NULL,

    quantity DECIMAL(10,2),
    unit VARCHAR(20),

    shipment_status ENUM(
        'CREATED',
        'PROCUREMENT',
        'QA_TESTING',
        'PACKAGING',
        'DOCUMENTATION',
        'READY_FOR_SHIPMENT',
        'SHIPPED',
        'DELIVERED'
    ) DEFAULT 'CREATED',

    expected_dispatch_date DATE,
    expected_delivery_date DATE,

    notes TEXT,

    created_by INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    FOREIGN KEY (created_by)
        REFERENCES users(user_id)
);

-- =========================================================
-- 4. MILESTONES TABLE
-- =========================================================

CREATE TABLE milestones (
    milestone_id INT PRIMARY KEY AUTO_INCREMENT,

    order_id INT NOT NULL,

    stage_name ENUM(
        'PROCUREMENT',
        'RAW_MATERIAL_VERIFIED',
        'QA_TESTING',
        'PACKAGING_STARTED',
        'PACKAGING_COMPLETED',
        'DOCUMENTS_UPLOADED',
        'CONTAINER_LOADING',
        'SHIPMENT_DISPATCHED',
        'DELIVERED'
    ) NOT NULL,

    status ENUM(
        'PENDING',
        'IN_PROGRESS',
        'COMPLETED'
    ) DEFAULT 'PENDING',

    remarks TEXT,

    completed_by INT,

    completed_at TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    FOREIGN KEY (completed_by)
        REFERENCES users(user_id)
);

-- =========================================================
-- 5. MEDIA FILES TABLE
-- =========================================================

CREATE TABLE media_files (
    media_id INT PRIMARY KEY AUTO_INCREMENT,

    order_id INT NOT NULL,

    milestone_id INT NULL,

    media_type ENUM(
        'PROCUREMENT_IMAGE',
        'PACKAGING_IMAGE',
        'QA_IMAGE',
        'LOADING_IMAGE'
    ) NOT NULL,

    file_name VARCHAR(255),

    file_url TEXT NOT NULL,

    file_size INT NULL,
    storage_key VARCHAR(512) NULL,

    uploaded_by INT,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    FOREIGN KEY (milestone_id)
        REFERENCES milestones(milestone_id),

    FOREIGN KEY (uploaded_by)
        REFERENCES users(user_id)
);

-- =========================================================
-- 6. DOCUMENTS TABLE
-- =========================================================

CREATE TABLE documents (
    document_id INT PRIMARY KEY AUTO_INCREMENT,

    order_id INT NOT NULL,

    document_type ENUM(
        'INVOICE',
        'BL_COPY',
        'COA',
        'PHYTOSANITARY_CERTIFICATE',
        'LAB_REPORT',
        'PACKING_LIST',
        'OTHER'
    ) NOT NULL,

    file_name VARCHAR(255),

    file_url TEXT NOT NULL,

    file_size INT NULL,
    storage_key VARCHAR(512) NULL,

    uploaded_by INT,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    FOREIGN KEY (uploaded_by)
        REFERENCES users(user_id)
);




-- =========================================================
-- 8. NOTIFICATIONS TABLE
-- =========================================================

CREATE TABLE notifications (
    notification_id INT PRIMARY KEY AUTO_INCREMENT,

    order_id INT NOT NULL,

    user_id INT NOT NULL,

    notification_type ENUM(
        'EMAIL',
        'WHATSAPP',
        'SMS'
    ),

    message TEXT,

    delivery_status ENUM(
        'PENDING',
        'SENT',
        'FAILED'
    ) DEFAULT 'PENDING',

    sent_at TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

-- =========================================================
-- 9. AUDIT LOGS TABLE
-- =========================================================

CREATE TABLE audit_logs (
    audit_id INT PRIMARY KEY AUTO_INCREMENT,

    user_id INT,

    action_type VARCHAR(100),

    target_table VARCHAR(100),

    target_id INT,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);




-- =========================================================
-- 11. LOGIN SESSIONS TABLE
-- =========================================================

CREATE TABLE login_sessions (
    session_id INT PRIMARY KEY AUTO_INCREMENT,

    user_id INT NOT NULL,

    jwt_token TEXT,

    ip_address VARCHAR(100),

    user_agent TEXT,

    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    expires_at TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);

-- =========================================================
-- PERFORMANCE INDEXES
-- =========================================================

CREATE INDEX idx_orders_customer
ON orders(customer_id);

CREATE INDEX idx_orders_status
ON orders(shipment_status);

CREATE INDEX idx_milestones_order
ON milestones(order_id);

CREATE INDEX idx_documents_order
ON documents(order_id);

CREATE INDEX idx_media_order
ON media_files(order_id);

CREATE INDEX idx_notifications_order
ON notifications(order_id);

CREATE INDEX idx_notifications_user
ON notifications(user_id);

CREATE INDEX idx_audit_user
ON audit_logs(user_id);

-- =========================================================
-- END OF SCHEMA
-- =========================================================