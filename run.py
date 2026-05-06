"""Entry point: `python run.py`."""
from app import create_app
from app.config import APP_PORT, OUTPUT_FOLDER, UPLOAD_FOLDER

app = create_app()

if __name__ == "__main__":
    print("启动 Hogel 图像生成器 API 服务...")
    print(f"上传目录: {UPLOAD_FOLDER}")
    print(f"输出目录: {OUTPUT_FOLDER}")
    print(f"监听地址: http://0.0.0.0:{APP_PORT}")
    app.run(debug=True, host="0.0.0.0", port=APP_PORT)
