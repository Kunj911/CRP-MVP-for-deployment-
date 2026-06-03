import os
import shutil
import json

debug_dir = r"C:\Users\Kunj Mistry\.gemini\antigravity-ide\brain\cc8e4113-1adb-4746-b2cb-cf01e24ad4e8\scratch"
with open(os.path.join(debug_dir, "cleanup_started.txt"), "w") as f:
    f.write("started")

print("Starting cleanups...")

workspace_dir = r"c:\Users\Kunj Mistry\Desktop\studies\Fittree\Relation Portal\Client Relationship Portal (MVP)"
root_dir = r"c:\Users\Kunj Mistry\Desktop\studies\Fittree\Relation Portal"

# 1. Approved files to delete
files_to_delete = [
    os.path.join(workspace_dir, "Docs", ".env"),
    os.path.join(workspace_dir, "backend", "scripts", "generate_hash.py"),
    os.path.join(workspace_dir, "backend", "scripts", "get_hashes.py"),
    os.path.join(workspace_dir, "backend", "scripts", "test_hash.py"),
    os.path.join(workspace_dir, "backend", "scripts", "test_db.py"),
    os.path.join(root_dir, "CONTEXT upto step 8.md"),
    os.path.join(root_dir, "CONTEXT_OVERVIEW till 21st.md"),
    os.path.join(root_dir, "CONTEXT_OVERVIEW.md"),
    os.path.join(root_dir, "backend_architecture_review.md"),
    os.path.join(root_dir, "email notification implementation.md"),
    os.path.join(root_dir, "final changes before deployment.md"),
    os.path.join(root_dir, "implementation of code review"),
    os.path.join(root_dir, "live_trace_pending_changes_checklist_markdown.md"),
]

deleted_log = []
failed_log = []

for f in files_to_delete:
    if os.path.exists(f):
        try:
            os.remove(f)
            print(f"✓ Deleted: {f}")
            deleted_log.append(f)
        except Exception as e:
            print(f"✗ Failed to delete {f}: {e}")
            failed_log.append(f"{f} ({e})")
    else:
        print(f"- File not found (already deleted): {f}")

# 2. Legacy schema file relocation
old_schema_path = os.path.join(root_dir, "table schema.sql")
legacy_dir = os.path.join(workspace_dir, "Docs", "legacy", "database")
new_schema_path = os.path.join(legacy_dir, "table schema.sql")

moved_log = []
if os.path.exists(old_schema_path):
    try:
        os.makedirs(legacy_dir, exist_ok=True)
        shutil.move(old_schema_path, new_schema_path)
        print(f"✓ Moved {old_schema_path} to {new_schema_path}")
        moved_log.append((old_schema_path, new_schema_path))
    except Exception as e:
        print(f"✗ Failed to move schema: {e}")
else:
    print("- Legacy table schema.sql not found at root (already moved).")

# 3. Write logs for validation report
logs = {
    "deleted": deleted_log,
    "failed": failed_log,
    "moved": moved_log
}

log_path = r"C:\Users\Kunj Mistry\.gemini\antigravity-ide\brain\cc8e4113-1adb-4746-b2cb-cf01e24ad4e8\scratch\cleanup_log.json"
with open(log_path, "w", encoding="utf-8") as out:
    json.dump(logs, out, indent=2)

with open(os.path.join(debug_dir, "cleanup_done.txt"), "w") as f:
    f.write("done")

print("Cleanup script finished.")
