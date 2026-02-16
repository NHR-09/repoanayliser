@echo off
echo ========================================
echo ARCHITECH Frontend - Installation Check
echo ========================================
echo.

cd frontend

echo [1/5] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Node.js is not installed
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
) else (
    echo [PASS] Node.js is installed
    node --version
)
echo.

echo [2/5] Checking npm installation...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] npm is not installed
    pause
    exit /b 1
) else (
    echo [PASS] npm is installed
    npm --version
)
echo.

echo [3/5] Checking package.json...
if exist package.json (
    echo [PASS] package.json exists
) else (
    echo [FAIL] package.json not found
    pause
    exit /b 1
)
echo.

echo [4/5] Checking source files...
if exist src\App.js (
    echo [PASS] App.js exists
) else (
    echo [FAIL] App.js not found
    pause
    exit /b 1
)

if exist src\components\AnalyzeRepo.js (
    echo [PASS] Components exist
) else (
    echo [FAIL] Components not found
    pause
    exit /b 1
)

if exist src\services\api.js (
    echo [PASS] API service exists
) else (
    echo [FAIL] API service not found
    pause
    exit /b 1
)
echo.

echo [5/5] Checking backend connectivity...
curl -s http://localhost:8000 >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Backend is not running at http://localhost:8000
    echo Please start the backend server before running frontend
) else (
    echo [PASS] Backend is running
)
echo.

echo ========================================
echo Installation Check Complete!
echo ========================================
echo.

if not exist node_modules\ (
    echo Dependencies not installed yet.
    echo Run: npm install
    echo.
) else (
    echo All checks passed!
    echo Ready to run: npm start
    echo.
)

pause
