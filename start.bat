@echo off
echo 启动 Hogel 图像处理系统...
echo.

echo 1. 检查Python依赖...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo 依赖安装失败，请手动安装
    pause
    exit /b 1
)

echo.
echo 2. 启动Flask后端API...
start cmd /k "python flask_hogel_api.py"

echo.
echo 3. 安装前端依赖...
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo 前端依赖安装失败，请手动安装
    pause
    exit /b 1
)

echo.
echo 4. 启动Vite前端开发服务器...
start cmd /k "npm start"

echo.
echo 系统启动完成！
echo.
echo 后端API: http://localhost:8000
echo 前端开发服务器: http://localhost:3000
echo.
echo 请等待前端服务器启动完成...
pause