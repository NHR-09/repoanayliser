@echo off
echo ========================================
echo ARCHITECH - Full Stack Startup
echo ========================================
echo.

echo Starting Backend Server...
start "ARCHITECH Backend" cmd /k "cd backend && python main.py"
timeout /t 3 /nobreak >nul

echo Starting Frontend Server...
start "ARCHITECH Frontend" cmd /k "cd frontend && npm start"

echo.
echo ========================================
echo ARCHITECH is starting...
echo ========================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Neo4j:    http://localhost:7474
echo ========================================
echo.
echo Press any key to stop all servers...
pause >nul

taskkill /FI "WindowTitle eq ARCHITECH Backend*" /T /F
taskkill /FI "WindowTitle eq ARCHITECH Frontend*" /T /F
