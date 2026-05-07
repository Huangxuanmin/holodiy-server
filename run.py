"""Entry point: `python run.py`."""
from app import create_app
from app.config import APP_PORT, OUTPUT_FOLDER, UPLOAD_FOLDER

app = create_app()

if __name__ == "__main__":
    print("启动 Hogel 图像生成器 API 服务...")
    print(f"上传目录: {UPLOAD_FOLDER}")
    print(f"输出目录: {OUTPUT_FOLDER}")
    print(f"监听地址: http://0.0.0.0:{APP_PORT}")
    # use_reloader=False: 避免 .py 保存时子进程重启，导致内存中的验证码被清空
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=APP_PORT)
