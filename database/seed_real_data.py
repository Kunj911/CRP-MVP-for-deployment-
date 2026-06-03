import os
import sys
from datetime import datetime, date, timedelta
import pymysql
import bcrypt
from db_config import get_db_connection

# Removed parse_env in favor of shared db_config

def hash_password(password: str) -> str:
    """Hash password using the application's bcrypt parameters"""
    pw_bytes = password.strip().encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")

def main():
    print("Connecting to MySQL database...")
    try:
        conn = get_db_connection(autocommit=False)
        cursor = conn.cursor()
        print("Successfully connected!")
    except Exception as e:
        print(f"Error connecting: {e}")
        sys.exit(1)
        
    try:
        tables = [
            "login_sessions",
            "audit_logs",
            "notifications",
            "media_files",
            "documents",
            "order_document_requirements",
            "order_events",
            "milestones",
            "orders",
            "users",
            "customers"
        ]
        
        print("\nClearing existing database tables...")
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            print(f"✓ Cleared table: {table}")
            
        print("\nResetting auto-increment indexes...")
        for table in reversed(tables):
            cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
            print(f"✓ Reset auto-increment: {table}")
            
        # Seed Customers
        print("\nSeeding Customers...")
        customers_data = [
            ("McCormick & Company", "Kunj", "kunj.fittree@gmail.com", "8866816365", "USA", "America/New_York", 
             "24 Schilling Road, Hunt Valley, Maryland 21031, USA", 2000),
            ("Olam Food Ingredients", "Roomi", "roominesh.fittree@gmail.com", "9081751379", "Singapore", "Asia/Singapore", 
             "7 Straits View, Marina One East Tower, Singapore 018936", 1500),
            ("Kerry Spice Group", "Yash", "yash.fittree@gmail.com", "9313049422", "Ireland", "Europe/Dublin", 
             "Tralee Road, Co. Kerry, Ireland", 1500),
            ("Pacific Spice Company Inc", "Vaidhehi", "vaidehifittree@gmail.com", "+918160777033", "USA", "America/Los_Angeles", 
             "6430 E. Slauson Ave, Commerce, CA 90040, USA", 2500)
        ]
        
        for name, contact, email, phone, country, tz, addr, quota in customers_data:
            cursor.execute(
                """INSERT INTO customers (company_name, contact_person, email, phone, country, timezone, address, storage_quota_mb) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, contact, email, phone, country, tz, addr, quota)
            )
        conn.commit()
        
        # Seed Users
        print("\nSeeding Platform Users...")
        internal_users = [
            ("Poonam", "poonam.fittree@gmail.com", "WAREHOUSE", "Warehouse@1234", "+91-9999911111"),
            ("Poonam QA", "poonam.qa.fittree@gmail.com", "QA", "QA@1234", "+91-9999922222"),
            ("Poonam Docs", "poonam.docs.fittree@gmail.com", "DOCUMENTATION", "Document@1234", "+91-9999933333"),
            ("Kunj Mistry", "kunjalpesh@gmail.com", "SUPER_ADMIN", "Iamtheadmin@1234", "+91-9999944444")
        ]
        
        for name, email, role, pwd, phone in internal_users:
            pw_hash = hash_password(pwd)
            cursor.execute(
                """INSERT INTO users (full_name, email, role, password_hash, phone, customer_id) 
                   VALUES (%s, %s, %s, %s, %s, NULL)""",
                (name, email, role, pw_hash, phone)
            )
            
        customer_users = [
            ("Kunj McCormick", "kunj.fittree@gmail.com", "Kunj@1234", "8866816365", "McCormick & Company"),
            ("Roomi Olam", "roominesh.fittree@gmail.com", "Roomi@1234", "9081751379", "Olam Food Ingredients"),
            ("Yash Kerry", "yash.fittree@gmail.com", "Yash@1234", "9313049422", "Kerry Spice Group"),
            ("Vaidhehi Pacific", "vaidehifittree@gmail.com", "Vaidhehi@1234", "+918160777033", "Pacific Spice Company Inc")
        ]
        
        for name, email, pwd, phone, company in customer_users:
            cursor.execute("SELECT customer_id FROM customers WHERE company_name = %s", (company,))
            cust_id = cursor.fetchone()[0]
            pw_hash = hash_password(pwd)
            cursor.execute(
                """INSERT INTO users (full_name, email, role, password_hash, phone, customer_id) 
                   VALUES (%s, %s, 'CUSTOMER', %s, %s, %s)""",
                (name, email, pw_hash, phone, cust_id)
            )
        conn.commit()
        
        # Get staff mapping
        cursor.execute("SELECT user_id, role FROM users WHERE role IN ('WAREHOUSE', 'QA', 'DOCUMENTATION', 'SUPER_ADMIN')")
        staff_mapping = {row[1]: row[0] for row in cursor.fetchall()}
        wh_user_id = staff_mapping["WAREHOUSE"]
        qa_user_id = staff_mapping["QA"]
        doc_user_id = staff_mapping["DOCUMENTATION"]
        admin_user_id = staff_mapping["SUPER_ADMIN"]
        
        # Get customer mapping
        cursor.execute("SELECT customer_id, company_name, country FROM customers")
        cust_mapping = {row[1]: (row[0], row[2]) for row in cursor.fetchall()}
        
        # Seed Orders
        print("\nSeeding Orders...")
        orders_data = [
            ("ORD-2026-MC01", "McCormick & Company", "Turmeric Powder", 15000.00, "KG", "DELIVERED", "2026-05-10", "2026-05-25"),
            ("ORD-2026-MC02", "McCormick & Company", "Black Pepper", 12000.00, "KG", "SHIPPED", "2026-05-20", "2026-06-05"),
            ("ORD-2026-MC03", "McCormick & Company", "Red Chilli Powder", 8000.00, "KG", "DOCUMENTATION", "2026-06-01", "2026-06-15"),
            ("ORD-2026-MC04", "McCormick & Company", "Garlic Powder", 5000.00, "KG", "QA_TESTING", "2026-06-05", "2026-06-20"),
            ("ORD-2026-MC05", "McCormick & Company", "Amchur Powder", 3000.00, "KG", "CREATED", "2026-06-12", "2026-06-28"),
            
            ("ORD-2026-OF01", "Olam Food Ingredients", "Cumin Powder", 20000.00, "KG", "DELIVERED", "2026-05-08", "2026-05-24"),
            ("ORD-2026-OF02", "Olam Food Ingredients", "Coriander Powder", 18000.00, "KG", "READY_FOR_SHIPMENT", "2026-05-28", "2026-06-12"),
            ("ORD-2026-OF03", "Olam Food Ingredients", "Ginger Powder", 10000.00, "KG", "PACKAGING", "2026-06-03", "2026-06-18"),
            ("ORD-2026-OF04", "Olam Food Ingredients", "White Pepper", 6000.00, "KG", "PROCUREMENT", "2026-06-10", "2026-06-25"),
            
            ("ORD-2026-KS01", "Kerry Spice Group", "Cinnamon Powder", 9000.00, "KG", "DELIVERED", "2026-05-12", "2026-05-27"),
            ("ORD-2026-KS02", "Kerry Spice Group", "Cardamom Powder", 4000.00, "KG", "SHIPPED", "2026-05-22", "2026-06-06"),
            ("ORD-2026-KS03", "Kerry Spice Group", "Onion Powder", 7500.00, "KG", "QA_TESTING", "2026-06-04", "2026-06-19"),
            ("ORD-2026-KS04", "Kerry Spice Group", "Amchur Powder", 5000.00, "KG", "PROCUREMENT", "2026-06-09", "2026-06-24"),
            
            ("ORD-2026-PS01", "Pacific Spice Company Inc", "Red Chilli Powder", 22000.00, "KG", "DELIVERED", "2026-05-09", "2026-05-24"),
            ("ORD-2026-PS02", "Pacific Spice Company Inc", "Turmeric Powder", 14000.00, "KG", "SHIPPED", "2026-05-21", "2026-06-05"),
            ("ORD-2026-PS03", "Pacific Spice Company Inc", "Black Pepper", 11000.00, "KG", "PACKAGING", "2026-06-02", "2026-06-17"),
            ("ORD-2026-PS04", "Pacific Spice Company Inc", "Cumin Powder", 3500.00, "KG", "CREATED", "2026-06-11", "2026-06-26"),
            ("ORD-2026-PS05", "Pacific Spice Company Inc", "Garlic Powder", 9000.00, "KG", "DOCUMENTATION", "2026-05-31", "2026-06-15")
        ]
        
        for code, company, product, qty, unit, status, expected_dispatch, expected_delivery in orders_data:
            cust_id, country = cust_mapping[company]
            full_notes = f"Payment status: Paid | Premium grade ground {product.lower()} shipment bound for {country}."
            cursor.execute(
                """INSERT INTO orders (order_code, customer_id, product_name, quantity, unit, shipment_status, expected_dispatch_date, expected_delivery_date, notes, created_by) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (code, cust_id, product, qty, unit, status, expected_dispatch, expected_delivery, full_notes, admin_user_id)
            )
        conn.commit()
        
        # Seed Milestones, Events, Documents, Checklist requirements, comments, audits
        print("\nSeeding dependent tables per order...")
        cursor.execute("SELECT order_id, order_code, shipment_status, expected_dispatch_date, expected_delivery_date, customer_id FROM orders")
        seeded_orders = cursor.fetchall()
        
        stages = [
            ("PROCUREMENT", wh_user_id, "Raw materials sourced and verified from select growers."),
            ("QA_VERIFICATION", qa_user_id, "Raw material physical verification complete."),
            ("QA_TESTING", qa_user_id, "Lab analysis cleared. Sample meets physical and chemical grades."),
            ("PACKAGING", wh_user_id, "Bags packaged, vacuum sealed, and palletized."),
            ("DOCUMENTATION", doc_user_id, "Export invoice, packing lists, and certificates prepared."),
            ("CONTAINER_LOADING", wh_user_id, "Loaded into container and verified cargo seals."),
            ("SHIPMENT_DISPATCH_ALERT", admin_user_id, "Dispatched via cargo transit."),
            ("DELIVERED", admin_user_id, "Delivered to port destination warehouse.")
        ]
        
        status_rank = {
            "CREATED": -1,
            "PROCUREMENT": 0,
            "QA_TESTING": 2,
            "PACKAGING": 3,
            "DOCUMENTATION": 4,
            "READY_FOR_SHIPMENT": 5,
            "SHIPPED": 6,
            "DELIVERED": 7
        }
        
        DOCUMENT_REQUIREMENTS = {
            "invoice": True,
            "purchase_order": True,
            "packing_list": True,
            "certificate_of_analysis": True,
            "product_specification": True,
            "bill_of_lading": False,
            "lab_report": False,
            "phytosanitary_certificate": False,
            "insurance_certificate": False,
            "certificate_of_origin": False,
            "other": False
        }

        for order_id, order_code, shipment_status, dispatch_date, delivery_date, customer_id in seeded_orders:
            cursor.execute("SELECT user_id FROM users WHERE customer_id = %s", (customer_id,))
            cust_user_id = cursor.fetchone()[0]
            status_index = status_rank.get(shipment_status, -1)
            
            # Log initial Order Event
            cursor.execute(
                """INSERT INTO order_events (order_id, event_type, description, created_at) 
                   VALUES (%s, 'status_changed', 'Order created and initial milestone set.', %s)""",
                (order_id, datetime.now() - timedelta(days=15))
            )
            
            # Seed Milestones
            milestone_ids = {}
            for idx, (stage_name, staff_id, desc) in enumerate(stages):
                if idx < status_index:
                    m_status = "COMPLETED"
                    completed_at = datetime.now() - timedelta(days=(status_index - idx) * 2)
                elif idx == status_index:
                    m_status = "IN_PROGRESS"
                    completed_at = None
                else:
                    m_status = "PENDING"
                    completed_at = None
                    
                cursor.execute(
                    """INSERT INTO milestones (order_id, stage_name, status, remarks, completed_by, completed_at, created_at) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (order_id, stage_name, m_status, desc, staff_id if m_status == "COMPLETED" else None, completed_at, datetime.now() - timedelta(days=14))
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                milestone_ids[stage_name] = cursor.fetchone()[0]
            
            # Seed documents and build requirements mapping
            seeded_docs = {}
            
            # 1. Invoice (Required)
            cursor.execute(
                """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                   VALUES (%s, 'invoice', %s, %s, 102400, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                (order_id, f"commercial_invoice_{order_code}.pdf", f"/uploads/{order_code}/documents/commercial_invoice_{order_code}.pdf", doc_user_id, admin_user_id, datetime.now() - timedelta(days=8))
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            seeded_docs["invoice"] = cursor.fetchone()[0]
            
            # 2. Product Spec (Required)
            cursor.execute(
                """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                   VALUES (%s, 'product_specification', %s, %s, 142000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                (order_id, f"product_specification_{order_code}.pdf", f"/uploads/{order_code}/documents/product_spec_{order_code}.pdf", doc_user_id, admin_user_id, datetime.now() - timedelta(days=8))
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            seeded_docs["product_specification"] = cursor.fetchone()[0]

            # 3. Purchase Order (Required)
            cursor.execute(
                """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                   VALUES (%s, 'purchase_order', %s, %s, 85000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                (order_id, f"purchase_order_{order_code}.pdf", f"/uploads/{order_code}/documents/purchase_order_{order_code}.pdf", cust_user_id, admin_user_id, datetime.now() - timedelta(days=9))
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            seeded_docs["purchase_order"] = cursor.fetchone()[0]

            if status_index >= 2: # QA Passed
                # Lab report and COA
                cursor.execute(
                    """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                       VALUES (%s, 'lab_report', %s, %s, 95000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                    (order_id, f"laboratory_analysis_{order_code}.pdf", f"/uploads/{order_code}/documents/lab_report_{order_code}.pdf", qa_user_id, admin_user_id, datetime.now() - timedelta(days=6))
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                seeded_docs["lab_report"] = cursor.fetchone()[0]
                
                cursor.execute(
                    """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                       VALUES (%s, 'certificate_of_analysis', %s, %s, 110000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                    (order_id, f"coa_{order_code}.pdf", f"/uploads/{order_code}/documents/coa_{order_code}.pdf", qa_user_id, admin_user_id, datetime.now() - timedelta(days=6))
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                seeded_docs["certificate_of_analysis"] = cursor.fetchone()[0]
                
                # Order Event
                cursor.execute(
                    """INSERT INTO order_events (order_id, event_type, description, created_at) 
                       VALUES (%s, 'document_approved', 'Certificate of Analysis (COA) approved.', %s)""",
                    (order_id, datetime.now() - timedelta(days=6))
                )
                
            if status_index >= 3: # Packaging Completed
                cursor.execute(
                    """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                       VALUES (%s, 'packing_list', %s, %s, 72000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                    (order_id, f"packing_list_{order_code}.pdf", f"/uploads/{order_code}/documents/packing_list_{order_code}.pdf", doc_user_id, admin_user_id, datetime.now() - timedelta(days=4))
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                seeded_docs["packing_list"] = cursor.fetchone()[0]

            if status_index >= 4: # Documentation Completed
                cursor.execute(
                    """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                       VALUES (%s, 'phytosanitary_certificate', %s, %s, 86000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                    (order_id, f"phytosanitary_certificate_{order_code}.pdf", f"/uploads/{order_code}/documents/phytosanitary_{order_code}.pdf", doc_user_id, admin_user_id, datetime.now() - timedelta(days=2))
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                seeded_docs["phytosanitary_certificate"] = cursor.fetchone()[0]
                
            if status_index >= 6: # Shipped
                cursor.execute(
                    """INSERT INTO documents (order_id, document_type, file_name, file_url, file_size, storage_key, uploaded_by, status, visibility, reviewed_by, reviewed_at) 
                       VALUES (%s, 'bill_of_lading', %s, %s, 192000, NULL, %s, 'approved', 'customer_visible', %s, %s)""",
                    (order_id, f"bill_of_lading_{order_code}.pdf", f"/uploads/{order_code}/documents/bill_of_lading_{order_code}.pdf", doc_user_id, admin_user_id, datetime.now() - timedelta(days=1))
                )
                cursor.execute("SELECT LAST_INSERT_ID()")
                seeded_docs["bill_of_lading"] = cursor.fetchone()[0]

                cursor.execute(
                    """INSERT INTO order_events (order_id, event_type, description, created_at) 
                       VALUES (%s, 'status_changed', 'Order status updated to SHIPPED.', %s)""",
                    (order_id, datetime.now() - timedelta(days=1))
                )

            # Insert document requirements checklist
            for dtype, req in DOCUMENT_REQUIREMENTS.items():
                uploaded = dtype in seeded_docs
                approved = uploaded # Seeded ones are pre-approved in this script
                doc_id = seeded_docs.get(dtype)
                
                cursor.execute(
                    """INSERT INTO order_document_requirements 
                       (order_id, document_type, required, uploaded, approved, uploaded_at, approved_at, approved_by, document_id) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        order_id, dtype, req, uploaded, approved, 
                        datetime.now() - timedelta(days=8) if uploaded else None,
                        datetime.now() - timedelta(days=7) if approved else None,
                        admin_user_id if approved else None,
                        doc_id
                    )
                )

            # Seed Media Files (Photos)
            if status_index >= 0:
                cursor.execute(
                    """INSERT INTO media_files (order_id, milestone_id, media_type, file_name, file_url, file_size, storage_key, uploaded_by) 
                       VALUES (%s, %s, 'PROCUREMENT_IMAGE', %s, %s, 245000, NULL, %s)""",
                    (order_id, milestone_ids["PROCUREMENT"], f"raw_material_{order_code}.jpg", f"/uploads/{order_code}/media/raw_material_{order_code}.jpg", wh_user_id)
                )
            if status_index >= 3:
                cursor.execute(
                    """INSERT INTO media_files (order_id, milestone_id, media_type, file_name, file_url, file_size, storage_key, uploaded_by) 
                       VALUES (%s, %s, 'PACKAGING_IMAGE', %s, %s, 189000, NULL, %s)""",
                    (order_id, milestone_ids["PACKAGING"], f"packaging_{order_code}.jpg", f"/uploads/{order_code}/media/packaging_{order_code}.jpg", wh_user_id)
                )

            # Seed Notifications with new structure (In-app support)
            cursor.execute(
                """INSERT INTO notifications (order_id, user_id, title, notification_type, message, delivery_status, sent_at, is_read, related_order_id) 
                   VALUES (%s, %s, 'Order Confirmed', 'order', %s, 'SENT', %s, 1, %s)""",
                (order_id, cust_user_id, f"Your export order {order_code} has been successfully registered.", datetime.now() - timedelta(days=10), order_id)
            )
            if status_index >= 2:
                cursor.execute(
                    """INSERT INTO notifications (order_id, user_id, title, notification_type, message, delivery_status, sent_at, is_read, related_order_id, related_document_id) 
                       VALUES (%s, %s, 'Quality Verification Passed', 'qa', %s, 'SENT', %s, 0, %s, %s)""",
                    (order_id, cust_user_id, f"QA analysis completed successfully for order {order_code}. High purity confirmed.", datetime.now() - timedelta(days=5), order_id, seeded_docs.get("certificate_of_analysis"))
                )
            if status_index >= 6:
                cursor.execute(
                    """INSERT INTO notifications (order_id, user_id, title, notification_type, message, delivery_status, sent_at, is_read, related_order_id) 
                       VALUES (%s, %s, 'Shipment Dispatched', 'shipment', %s, 'SENT', %s, 0, %s)""",
                    (order_id, cust_user_id, f"Shipment dispatched for order {order_code}. Vessel in transit.", datetime.now() - timedelta(days=2), order_id)
                )
                
            # Audit logs
            cursor.execute(
                "INSERT INTO audit_logs (user_id, action_type, target_table, target_id, description) VALUES (%s, 'create', 'orders', %s, %s)",
                (admin_user_id, order_id, f"Admin created order {order_code}.")
            )

        conn.commit()
        print("✓ Database seeding complete!")
        
        print("\n" + "=" * 60)
        print("                SEEDING COMPLETE - SUMMARY")
        print("=" * 60)
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cursor.fetchone()[0]
            print(f"Table {table:30}: {cnt} records")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during database seeding transaction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()
        print("\nDatabase connection closed. Seeding complete.")

if __name__ == "__main__":
    main()
