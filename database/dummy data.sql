use live_trace_dashboard;
# Live-Trace Export Dashboard
-- =========================================================
-- CUSTOMERS
-- =========================================================

INSERT INTO customers (
    company_name,
    contact_person,
    email,
    phone,
    country,
    timezone,
    address
)
VALUES
(
    'SpiceWorld Imports Ltd',
    'Michael Carter',
    'michael@spiceworld.com',
    '+44-7744552233',
    'United Kingdom',
    'Europe/London',
    '221B Trade Street, London'
),
(
    'Global Herb Traders',
    'Emily Watson',
    'emily@globalherb.com',
    '+1-202-555-0147',
    'United States',
    'America/New_York',
    'New York Trade District'
),
(
    'Orient Spice Market',
    'Kenji Takahashi',
    'kenji@orientspice.jp',
    '+81-90-2233-9988',
    'Japan',
    'Asia/Tokyo',
    'Tokyo Port Business Center'
);

-- =========================================================
-- USERS
-- =========================================================

INSERT INTO users (
    full_name,
    email,
    phone,
    password_hash,
    role,
    customer_id
)
VALUES
(
    'Kunal Mehta',
    'admin@livetrace.com',
    '+91-9876543210',
    '$2b$12$1o0mE2f1z66HovEgev7VTOLerJ3aT4Z0ER1PxqYpjBpvrkwzD.fMe',
    'SUPER_ADMIN',
    NULL
),
(
    'Ravi Patel',
    'warehouse@livetrace.com',
    '+91-9988776655',
    '$2b$12$kb3Dd7urSqq9WiQoEXcFTeqmqn/Mz7eovdsdbGHEl7VZn7o2lVbgW',
    'WAREHOUSE',
    NULL
),
(
    'Priya Shah',
    'qa@livetrace.com',
    '+91-8877665544',
    '$2b$12$Vy21ofc3JqMni1jDxreeLujgThkhWW1u.ehp0RR8u0t3wJmwOYl96',
    'QA',
    NULL
),
(
    'Arjun Desai',
    'docs@livetrace.com',
    '+91-7766554433',
    '$2b$12$.M0KRIpW1qlXzL9UeW4JMuD05pG74ECYc9FQTiS/aixYc06VSKBTS',
    'DOCUMENTATION',
    NULL
),
(
    'Michael Carter',
    'client1@spiceworld.com',
    '+44-7744552233',
    '$2b$12$ve6hPNpudtQnWkDMOMYzxuW8OmjaV2A/bM16QWQtGmVZiMBGpfGGS',
    'CUSTOMER',
    1
),
(
    'Emily Watson',
    'client2@globalherb.com',
    '+1-202-555-0147',
    '$2b$12$Qdofpg5leqUSq6dThCmydO7/sPpM2Tn/f7S3mftdBvZIodNLzCynu',
    'CUSTOMER',
    2
);

-- =========================================================
-- ORDERS
-- =========================================================

INSERT INTO orders (
    order_code,
    customer_id,
    product_name,
    quantity,
    unit,
    shipment_status,
    expected_dispatch_date,
    expected_delivery_date,
    notes,
    created_by
)
VALUES
(
    'ORD-2026-001',
    1,
    'Turmeric Fingers Grade A',
    25000,
    'KG',
    'PACKAGING',
    '2026-06-10',
    '2026-06-25',
    'High-curcumin export batch',
    1
),
(
    'ORD-2026-002',
    2,
    'Whole Black Pepper',
    18000,
    'KG',
    'QA_TESTING',
    '2026-06-14',
    '2026-06-29',
    'Steam sterilized shipment',
    1
),
(
    'ORD-2026-003',
    3,
    'Green Cardamom Premium',
    8000,
    'KG',
    'DOCUMENTATION',
    '2026-06-18',
    '2026-07-02',
    'Export-grade premium selection',
    1
);

-- =========================================================
-- MILESTONES
-- =========================================================

INSERT INTO milestones (
    order_id,
    stage_name,
    status,
    remarks,
    completed_by,
    completed_at
)
VALUES
(
    1,
    'PROCUREMENT',
    'COMPLETED',
    'Raw turmeric procured from Erode farmers',
    2,
    NOW()
),
(
    1,
    'RAW_MATERIAL_VERIFIED',
    'COMPLETED',
    'Moisture and quality verified',
    3,
    NOW()
),
(
    1,
    'PACKAGING_STARTED',
    'IN_PROGRESS',
    'Vacuum packaging initiated',
    2,
    NOW()
),
(
    2,
    'PROCUREMENT',
    'COMPLETED',
    'Pepper sourced from Kerala suppliers',
    2,
    NOW()
),
(
    2,
    'QA_TESTING',
    'IN_PROGRESS',
    'Lab testing underway',
    3,
    NOW()
),
(
    3,
    'DOCUMENTS_UPLOADED',
    'COMPLETED',
    'Export documents uploaded',
    4,
    NOW()
);

-- =========================================================
-- MEDIA FILES
-- =========================================================

INSERT INTO media_files (
    order_id,
    milestone_id,
    media_type,
    file_name,
    file_url,
    uploaded_by
)
VALUES
(
    1,
    1,
    'PROCUREMENT_IMAGE',
    'turmeric_procurement_1.jpg',
    '/uploads/ORD-2026-001/procurement/turmeric_procurement_1.jpg',
    2
),
(
    1,
    3,
    'PACKAGING_IMAGE',
    'packaging_line.jpg',
    '/uploads/ORD-2026-001/packaging/packaging_line.jpg',
    2
),
(
    2,
    5,
    'QA_IMAGE',
    'pepper_lab_testing.jpg',
    '/uploads/ORD-2026-002/qa/pepper_lab_testing.jpg',
    3
),
(
    3,
    6,
    'LOADING_IMAGE',
    'container_loading.jpg',
    '/uploads/ORD-2026-003/loading/container_loading.jpg',
    2
);

-- =========================================================
-- DOCUMENTS
-- =========================================================

INSERT INTO documents (
    order_id,
    document_type,
    file_name,
    file_url,
    uploaded_by
)
VALUES
(
    1,
    'LAB_REPORT',
    'turmeric_lab_report.pdf',
    '/uploads/ORD-2026-001/documents/turmeric_lab_report.pdf',
    3
),
(
    1,
    'INVOICE',
    'invoice_001.pdf',
    '/uploads/ORD-2026-001/documents/invoice_001.pdf',
    4
),
(
    2,
    'COA',
    'black_pepper_coa.pdf',
    '/uploads/ORD-2026-002/documents/black_pepper_coa.pdf',
    3
),
(
    3,
    'BL_COPY',
    'bill_of_lading.pdf',
    '/uploads/ORD-2026-003/documents/bill_of_lading.pdf',
    4
),
(
    3,
    'PHYTOSANITARY_CERTIFICATE',
    'phytosanitary_certificate.pdf',
    '/uploads/ORD-2026-003/documents/phytosanitary_certificate.pdf',
    4
);




-- =========================================================
-- NOTIFICATIONS
-- =========================================================

INSERT INTO notifications (
    order_id,
    user_id,
    notification_type,
    message,
    delivery_status,
    sent_at
)
VALUES
(
    1,
    5,
    'EMAIL',
    'Packaging for your turmeric shipment has started.',
    'SENT',
    NOW()
),
(
    2,
    6,
    'WHATSAPP',
    'QA testing for your black pepper shipment is underway.',
    'SENT',
    NOW()
),
(
    3,
    5,
    'EMAIL',
    'Bill of Lading has been uploaded for your shipment.',
    'SENT',
    NOW()
);

-- =========================================================
-- AUDIT LOGS
-- =========================================================

INSERT INTO audit_logs (
    user_id,
    action_type,
    target_table,
    target_id,
    description
)
VALUES
(
    1,
    'CREATE_ORDER',
    'orders',
    1,
    'Created turmeric export order ORD-2026-001'
),
(
    2,
    'UPLOAD_IMAGE',
    'media_files',
    1,
    'Uploaded procurement image for turmeric shipment'
),
(
    3,
    'UPLOAD_QA_REPORT',
    'documents',
    1,
    'Uploaded QA report for turmeric batch'
),
(
    4,
    'UPLOAD_DOCUMENT',
    'documents',
    4,
    'Uploaded BL copy for cardamom shipment'
);




-- =========================================================
-- LOGIN SESSIONS
-- =========================================================

INSERT INTO login_sessions (
    user_id,
    jwt_token,
    ip_address,
    user_agent,
    expires_at
)
VALUES
(
    1,
    'dummy_jwt_token_001',
    '192.168.1.10',
    'Chrome Browser',
    DATE_ADD(NOW(), INTERVAL 1 DAY)
),
(
    5,
    'dummy_jwt_token_002',
    '192.168.1.20',
    'Safari Browser',
    DATE_ADD(NOW(), INTERVAL 1 DAY)
);


