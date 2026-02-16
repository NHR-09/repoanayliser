@echo off
echo ========================================
echo ARCHITECH Frontend Setup
echo ========================================
echo.

cd frontend

if not exist "node_modules\" (
    echo Installing dependencies...
    call npm install
    echo.
)

echo Starting React development server...
echo Frontend will be available at http://localhost:3000
echo.
echo Make sure backend is running at http://localhost:8000
echo.

call npm start
