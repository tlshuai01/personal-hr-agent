@echo off
REM 从浏览器 Cookie 登录 Boss CLI（无二维码，不受 PS 执行策略限制）
setlocal
set BOSS_PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe
if not exist "%BOSS_PY%" set BOSS_PY=python

cd /d "%~dp0.."
echo 使用 Python: %BOSS_PY%
echo 提示: Chrome 登录 zhipin.com 后请完全退出 Chrome
echo.

"%BOSS_PY%" "%~dp0boss-login-cookie.py" %*
exit /b %ERRORLEVEL%
