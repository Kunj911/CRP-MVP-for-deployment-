"""
scripts/seed_db.py

A utility script to populate the Live-Trace database from an Excel (.xlsx) or CSV file.
Requires `pandas` and `openpyxl`.

Usage:
    python -m scripts.seed_db path/to/your/dataset.xlsx
"""

import sys
import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add the parent directory to the sys path so we can import from `app`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.user import User
from app.models.order import Order
from app.core.security import hash_password


def seed_database(file_path: str):
    print(f"Reading dataset from {file_path}...")
    
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        print("Unsupported file format. Please use .csv or .xlsx")
        return

    # Clean column names (strip whitespace, lowercase, replace spaces with underscores)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    db: Session = SessionLocal()
    
    try:
        # Example mapping logic. You will need to adjust these column names 
        # based on the exact headers in your actual dataset.
        
        # 1. Seed Customers
        print("Seeding Customers...")
        for _, row in df.iterrows():
            customer_name = row.get("company_name", "Unknown Company")
            if pd.isna(customer_name):
                continue
                
            # Check if exists
            existing_customer = db.query(Customer).filter_by(company_name=customer_name).first()
            if not existing_customer:
                customer = Customer(
                    company_name=customer_name,
                    contact_person=row.get("contact_person", "N/A"),
                    email=row.get("customer_email", "admin@company.com"),
                    phone=row.get("customer_phone", "0000000000"),
                    address=row.get("address", "N/A"),
                )
                db.add(customer)
        db.commit()

        # 2. Seed Users (e.g., creating login accounts for customers)
        print("Seeding Users...")
        # Add your user logic here...

        # 3. Seed Orders
        print("Seeding Orders...")
        # Add your order logic here...

        print("Database seeded successfully!")

    except IntegrityError as e:
        db.rollback()
        print(f"Database Integrity Error: {e}")
    except Exception as e:
        db.rollback()
        print(f"An unexpected error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide the path to your dataset file.")
        print("Usage: python -m scripts.seed_db data.xlsx")
        sys.exit(1)
        
    dataset_path = sys.argv[1]
    if not os.path.exists(dataset_path):
        print(f"File not found: {dataset_path}")
        sys.exit(1)
        
    seed_database(dataset_path)
