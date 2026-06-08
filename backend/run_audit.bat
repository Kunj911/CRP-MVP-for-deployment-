@echo off
cd /d "c:\Users\Kunj Mistry\Desktop\studies\Fittree\Relation Portal\Client Relationship Portal (MVP)\backend"
.\venv\Scripts\python.exe run_security_audit.py > audit_run_log.txt 2>&1
echo Exit code: %errorlevel% >> audit_run_log.txt
