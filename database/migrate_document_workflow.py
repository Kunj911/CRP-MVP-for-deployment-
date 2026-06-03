import pymysql
from db_config import get_db_connection

def run_migration():
    print("Connecting to database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Modify document_type enum
    print("Modifying document_type column to support new lowercase enums...")
    try:
        cursor.execute("""
            ALTER TABLE documents MODIFY COLUMN document_type ENUM(
                'INVOICE', 'BL_COPY', 'COA', 'PHYTOSANITARY_CERTIFICATE', 'LAB_REPORT', 'PACKING_LIST', 'OTHER',
                'invoice', 'bill_of_lading', 'lab_report', 'packing_list', 'certificate_of_analysis', 
                'phytosanitary_certificate', 'product_specification', 'insurance_certificate', 
                'purchase_order', 'certificate_of_origin', 'other'
            ) NOT NULL;
        """)
        conn.commit()
        print(" -> document_type column modified successfully!")
    except Exception as e:
        print(f" -> Error modifying document_type: {e}")

    # 2. Add columns safely to documents table
    columns_to_add = [
        ("status", "ENUM('draft', 'uploaded', 'under_review', 'approved', 'rejected', 'archived') NOT NULL DEFAULT 'uploaded'"),
        ("visibility", "ENUM('internal', 'customer_visible', 'admin_only') NOT NULL DEFAULT 'internal'"),
        ("reviewed_by", "INT NULL"),
        ("reviewed_at", "TIMESTAMP NULL"),
        ("created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ("is_deleted", "TINYINT(1) NOT NULL DEFAULT 0")
    ]
    
    for col_name, col_def in columns_to_add:
        print(f"Adding column '{col_name}' if missing to documents...")
        try:
            cursor.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_def};")
            conn.commit()
            print(f" -> Column '{col_name}' added successfully!")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f" -> Column '{col_name}' already exists.")
            else:
                print(f" -> Error adding column '{col_name}': {e}")
                
    # 3. Add foreign key constraint for reviewed_by on documents
    print("Adding foreign key constraint for reviewed_by...")
    try:
        cursor.execute("""
            ALTER TABLE documents ADD CONSTRAINT fk_documents_reviewed_by 
            FOREIGN KEY (reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL;
        """)
        conn.commit()
        print(" -> Constraint 'fk_documents_reviewed_by' added successfully!")
    except Exception as e:
        if "Duplicate key name" in str(e) or "already exists" in str(e) or "Can't write; duplicate key" in str(e):
            print(" -> Constraint already exists.")
        else:
            print(f" -> Error adding foreign key: {e}")

    # 4. Create order_events table
    print("Creating order_events table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_events (
                event_id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        print(" -> order_events table checked/created successfully!")
    except Exception as e:
        print(f" -> Error creating order_events table: {e}")

    # 5. Create order_document_requirements table
    print("Creating order_document_requirements table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_document_requirements (
                requirement_id INT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                document_type ENUM(
                    'invoice', 'bill_of_lading', 'lab_report', 'packing_list', 'certificate_of_analysis', 
                    'phytosanitary_certificate', 'product_specification', 'insurance_certificate', 
                    'purchase_order', 'certificate_of_origin', 'other'
                ) NOT NULL,
                required BOOLEAN NOT NULL DEFAULT FALSE,
                uploaded BOOLEAN NOT NULL DEFAULT FALSE,
                approved BOOLEAN NOT NULL DEFAULT FALSE,
                uploaded_at TIMESTAMP NULL,
                approved_at TIMESTAMP NULL,
                approved_by INT NULL,
                document_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                FOREIGN KEY (approved_by) REFERENCES users(user_id) ON DELETE SET NULL,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE SET NULL,
                UNIQUE KEY uq_order_doc_type (order_id, document_type)
            );
        """)
        conn.commit()
        print(" -> order_document_requirements table created successfully!")
    except Exception as e:
        print(f" -> Error creating order_document_requirements table: {e}")

    # 6. Modify notifications table for in-app notification tracking
    print("Modifying notifications table for in-app support...")
    try:
        cursor.execute("ALTER TABLE notifications ADD COLUMN title VARCHAR(255) NULL;")
        conn.commit()
        print(" -> Title column added successfully!")
    except Exception as e:
        if "Duplicate column name" in str(e):
            print(" -> Title column already exists.")
        else:
            print(f" -> Error adding title column: {e}")
            
    try:
        cursor.execute("""
            ALTER TABLE notifications MODIFY COLUMN notification_type ENUM(
                'EMAIL', 'WHATSAPP', 'SMS', 'order', 'document', 'shipment', 'system', 'qa', 'payment'
            ) NOT NULL;
        """)
        conn.commit()
        print(" -> notification_type column modified successfully!")
    except Exception as e:
        print(f" -> Error modifying notification_type: {e}")

    columns_to_add_notifications = [
        ("related_order_id", "INT NULL"),
        ("related_document_id", "INT NULL"),
        ("is_read", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    ]
    
    for col_name, col_def in columns_to_add_notifications:
        print(f"Adding column '{col_name}' if missing to notifications...")
        try:
            cursor.execute(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_def};")
            conn.commit()
            print(f" -> Column '{col_name}' added successfully!")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f" -> Column '{col_name}' already exists.")
            else:
                print(f" -> Error adding column '{col_name}': {e}")
                
    # Add foreign key constraints to notifications
    print("Adding foreign key constraints to notifications...")
    try:
        cursor.execute("""
            ALTER TABLE notifications ADD CONSTRAINT fk_notifications_related_order 
            FOREIGN KEY (related_order_id) REFERENCES orders(order_id) ON DELETE CASCADE;
        """)
        conn.commit()
        print(" -> Constraint 'fk_notifications_related_order' added successfully!")
    except Exception as e:
        if "Duplicate key name" in str(e) or "already exists" in str(e) or "Can't write; duplicate key" in str(e):
            print(" -> Order constraint already exists.")
        else:
            print(f" -> Error adding order constraint: {e}")
            
    try:
        cursor.execute("""
            ALTER TABLE notifications ADD CONSTRAINT fk_notifications_related_document 
            FOREIGN KEY (related_document_id) REFERENCES documents(document_id) ON DELETE SET NULL;
        """)
        conn.commit()
        print(" -> Constraint 'fk_notifications_related_document' added successfully!")
    except Exception as e:
        if "Duplicate key name" in str(e) or "already exists" in str(e) or "Can't write; duplicate key" in str(e):
            print(" -> Document constraint already exists.")
        else:
            print(f" -> Error adding document constraint: {e}")

    # 7. Migrate existing orders
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

    print("Migrating requirements for existing orders...")
    try:
        cursor.execute("SELECT order_id FROM orders;")
        order_ids = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(order_ids)} orders.")
        
        for oid in order_ids:
            for dtype, req in DOCUMENT_REQUIREMENTS.items():
                # Check if a document of this type exists for this order
                # Map lowercase to legacy uppercase enums if needed
                legacy_types = []
                if dtype == "invoice": legacy_types = ["INVOICE"]
                elif dtype == "packing_list": legacy_types = ["PACKING_LIST"]
                elif dtype == "certificate_of_analysis": legacy_types = ["COA"]
                elif dtype == "lab_report": legacy_types = ["LAB_REPORT"]
                elif dtype == "bill_of_lading": legacy_types = ["BL_COPY"]
                elif dtype == "phytosanitary_certificate": legacy_types = ["PHYTOSANITARY_CERTIFICATE"]
                elif dtype == "other": legacy_types = ["OTHER"]
                
                type_conditions = [dtype] + legacy_types
                placeholders = ", ".join(["%s"] * len(type_conditions))
                
                cursor.execute(f"""
                    SELECT document_id, uploaded_at, status, reviewed_at, reviewed_by 
                    FROM documents 
                    WHERE order_id = %s AND document_type IN ({placeholders}) AND is_deleted = 0
                    ORDER BY uploaded_at DESC LIMIT 1;
                """, [oid] + type_conditions)
                
                doc = cursor.fetchone()
                
                uploaded = False
                uploaded_at = None
                approved = False
                approved_at = None
                approved_by = None
                document_id = None
                
                if doc:
                    document_id = doc[0]
                    uploaded = True
                    uploaded_at = doc[1]
                    status = doc[2]
                    approved_at = doc[3]
                    approved_by = doc[4]
                    if status == "approved":
                        approved = True
                
                cursor.execute("""
                    INSERT INTO order_document_requirements 
                    (order_id, document_type, required, uploaded, approved, uploaded_at, approved_at, approved_by, document_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        required = VALUES(required),
                        uploaded = VALUES(uploaded),
                        approved = VALUES(approved),
                        uploaded_at = VALUES(uploaded_at),
                        approved_at = VALUES(approved_at),
                        approved_by = VALUES(approved_by),
                        document_id = VALUES(document_id);
                """, (oid, dtype, req, uploaded, approved, uploaded_at, approved_at, approved_by, document_id))
        
        conn.commit()
        print(" -> Migration of order requirements completed successfully!")
    except Exception as e:
        print(f" -> Error during order migration: {e}")

    conn.close()
    print("Migration finished!")

if __name__ == "__main__":
    run_migration()
