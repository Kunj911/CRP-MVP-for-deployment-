@echo off
cd /d "c:\Users\Kunj Mistry\Desktop\studies\Fittree\Relation Portal\Client Relationship Portal (MVP)\backend"
set APP_ENV=development
set DEBUG=True
.\venv\Scripts\python.exe -m uvicorn main:app --port 8001
