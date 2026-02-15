@echo off
echo ========================================
echo ARCHITECH - GitHub Push Script
echo ========================================
echo.

REM Check if git is initialized
if not exist .git (
    echo Initializing Git repository...
    git init
    echo.
)

REM Add all files
echo Adding files to Git...
git add .
echo.

REM Create commit
echo Creating commit...
git commit -m "Initial commit: ARCHITECH - Architectural Recovery Platform"
echo.

REM Instructions for GitHub
echo ========================================
echo NEXT STEPS:
echo ========================================
echo 1. Go to https://github.com/new
echo 2. Create a new repository named "ARCHITECH"
echo 3. DO NOT initialize with README, .gitignore, or license
echo 4. Copy the repository URL (e.g., https://github.com/username/ARCHITECH.git)
echo 5. Run these commands:
echo.
echo    git remote add origin YOUR_REPO_URL
echo    git branch -M main
echo    git push -u origin main
echo.
echo ========================================
pause
