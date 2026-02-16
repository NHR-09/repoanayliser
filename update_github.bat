@echo off
echo ========================================
echo ARCHITECH - Update GitHub Repository
echo ========================================
echo.

REM Check git status
echo Checking current status...
git status
echo.

REM Add all changes
echo Adding updated files...
git add .
echo.

REM Show what will be committed
echo Files to be committed:
git diff --cached --name-only
echo.

REM Commit changes
set /p commit_msg="Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" set commit_msg=Update: Enhanced .gitignore for API key protection

echo.
echo Committing with message: %commit_msg%
git commit -m "%commit_msg%"
echo.

REM Push to GitHub
echo Pushing to GitHub...
git push
echo.

echo ========================================
echo Done! Changes pushed to GitHub.
echo ========================================
pause
