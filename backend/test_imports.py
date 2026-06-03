import os
import sys
from sqlalchemy.orm import configure_mappers

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Client Relationship Portal (MVP)", "backend")))

from app.database.connection import Base
import app.models
import app.services.upload_service
import app.services.document_vault_service
import app.services.order_service
import app.services.milestone_service
import app.services.auth_service

def verify():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(dir_path, "validation_output.txt")
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write("SQLAlchemy mapper compilation & imports validation started...\n")
        try:
            configure_mappers()
            out.write("✓ configure_mappers() succeeded!\n")
            
            out.write("\nSQLAlchemy Models verified:\n")
            for table_name in Base.metadata.tables.keys():
                out.write(f"  - Table: {table_name}\n")
                
            out.write("\nVerification successfully completed! All models and services imported cleanly.\n")
        except Exception as e:
            out.write(f"\nError during compilation: {e}\n")

if __name__ == "__main__":
    verify()
