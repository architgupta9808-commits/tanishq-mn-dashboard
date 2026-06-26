@echo off
:: Creates a desktop shortcut to the Tanishq MN Dashboard
set DASHBOARD_URL=https://tanishq-mn-dashboard.streamlit.app
set SHORTCUT_NAME=Tanishq MN Dashboard

echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\%SHORTCUT_NAME%.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "C:\Program Files\Google\Chrome\Application\chrome.exe" >> CreateShortcut.vbs
echo oLink.Arguments = "--app=%DASHBOARD_URL% --window-size=1200,800" >> CreateShortcut.vbs
echo oLink.Description = "Tanishq MN Sales Dashboard" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo Desktop shortcut created: %SHORTCUT_NAME%
echo Double-click it to open the dashboard as a standalone app (no browser chrome)
pause
