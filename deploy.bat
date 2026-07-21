@echo off
REM Dad's Desk - scan for fresh data, then deploy to Firebase. Windows.
echo Running scan...
python scan.py --once
echo Deploying to Firebase...
firebase deploy --only hosting
echo Done. Your app is live.
pause
