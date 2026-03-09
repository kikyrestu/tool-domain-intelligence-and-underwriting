@echo off
title Domain IQ Server
cd /d D:\PROJECT\client-10
python -m uvicorn app.main:app --port 8000
pause
