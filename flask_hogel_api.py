import os
import sys
import tempfile
import shutil
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
from PIL import Image
import io
import base64

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_image_preview(image_path, max_size=(200, 200)):
    """生成图像的预览图"""
    try:
        with Image.open(image_path) as img:
            # 转换为RGB模式（如果是RGBA）
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # 调整大小
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"生成预览图失败: {e}")
        return None

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'message': 'Hogel API 服务运行正常'
    })

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """上传文件接口"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # 生成预览图
            preview_url = get_image_preview(file_path)
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            
            uploaded_files.append({
                'filename': filename,
                'size': file_size,
                'preview_url': preview_url,
                'path': file_path
            })
    
    return jsonify({
        'success': True,
        'message': f'成功上传 {len(uploaded_files)} 个文件',
        'files': uploaded_files
    })

@app.route('/api/generate-hogel', methods=['POST'])
def generate_hogel():
    """生成hogel图像接口"""
    try:
        # 检查文件上传
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': '没有文件上传'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        # 获取参数
        C = request.form.get('C', type=int, default=10)
        width = request.form.get('width', type=int, default=500)
        height = request.form.get('height', type=int, default=None)
        quality = request.form.get('quality', type=int, default=95)
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_input_dir:
            with tempfile.TemporaryDirectory() as temp_output_dir:
                # 保存上传的文件到临时目录
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(temp_input_dir, filename)
                        file.save(file_path)
                
                # 检查是否有文件保存成功
                saved_files = [f for f in os.listdir(temp_input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
                if not saved_files:
                    return jsonify({'success': False, 'error': '没有有效的图像文件'}), 400
                
                # 直接调用 hogel_processor.py 的函数
                try:
                    # 导入 hogel_processor 模块
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("hogel_processor", "hogel_processor.py")
                    hogel_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hogel_module)
                    
                    # 调用处理函数
                    hogel_module.process_hogel_images(
                        input_folder=temp_input_dir,
                        output_folder=temp_output_dir,
                        C=C,
                        hogel_width_fixed=width,
                        hogel_height_fixed=height if height else None,
                        quality=quality
                    )
                    
                    process_log = "处理成功完成"
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'处理失败: {str(e)}'
                    }), 500
                
                # 获取生成的hogel文件
                hogel_files = [f for f in os.listdir(temp_output_dir) if f.lower().endswith('.jpg')]
                hogel_files.sort()
                
                hogels = []
                for hogel_file in hogel_files:
                    hogel_path = os.path.join(temp_output_dir, hogel_file)
                    
                    # 生成预览图
                    preview_url = get_image_preview(hogel_path)
                    
                    # 获取文件信息
                    file_size = os.path.getsize(hogel_path)
                    
                    # 创建唯一的输出文件名
                    output_filename = f"hogel_{len(hogels) + 1:03d}.jpg"
                    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                    
                    # 复制到永久输出目录
                    shutil.copy2(hogel_path, output_path)
                    
                    hogels.append({
                        'name': output_filename,
                        'size': f"{file_size / 1024:.1f} KB",
                        'preview_url': preview_url,
                        'download_url': f'/api/download/{output_filename}'
                    })
                
                return jsonify({
                    'success': True,
                    'message': f'成功生成 {len(hogels)} 个 hogel 图像',
                    'hogels': hogels,
                    'log': process_log
                })
    
    except Exception as e:
        print(f"生成hogel时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """下载文件接口"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'success': False, 'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-all', methods=['GET'])
def download_all():
    """下载所有hogel文件（打包为zip）"""
    try:
        import zipfile
        from io import BytesIO
        
        # 创建内存中的zip文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in os.listdir(app.config['OUTPUT_FOLDER']):
                file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                if os.path.isfile(file_path) and filename.lower().endswith('.jpg'):
                    zf.write(file_path, filename)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='hogel_images.zip'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-outputs', methods=['POST'])
def clear_outputs():
    """清空输出目录"""
    try:
        for filename in os.listdir(app.config['OUTPUT_FOLDER']):
            file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': '输出目录已清空'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
def get_default_settings():
    """获取默认设置"""
    return jsonify({
        'success': True,
        'settings': {
            'hogelCount': 10,
            'hogelWidth': 500,
            'heightMode': 'fixed',
            'hogelHeight': 500,
            'quality': 95,
            'enableAntiAliasing': True,
            'enableOptimization': True
        }
    })

@app.route('/api/estimate', methods=['POST'])
def estimate_processing():
    """预估处理性能"""
    try:
        data = request.json
        file_count = data.get('fileCount', 0)
        total_size = data.get('totalSize', 0)  # bytes
        
        # 简单的预估逻辑
        processing_time = max(2, round(file_count * 0.5 + total_size / (1024 * 1024) * 0.1))
        memory_usage = round(total_size / (1024 * 1024) * 1.5)
        output_size = round(total_size * 0.8 / (1024 * 1024))
        
        return jsonify({
            'success': True,
            'estimate': {
                'processingTime': f'~{processing_time}s',
                'memoryUsage': f'~{memory_usage}MB',
                'outputSize': f'~{output_size}MB'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def serve_frontend():
    """提供前端页面"""
    return send_from_directory('.', 'vue_hogel.html')

@app.route('/vue_hogel.css')
def serve_css():
    """提供CSS文件"""
    return send_from_directory('.', 'vue_hogel.css')

@app.route('/vue_hogel.js')
def serve_js():
    """提供JavaScript文件"""
    return send_from_directory('.', 'vue_hogel.js')

if __name__ == '__main__':
    print("启动 Hogel 图像生成器 API 服务...")
    print(f"上传目录: {UPLOAD_FOLDER}")
    print(f"输出目录: {OUTPUT_FOLDER}")
    print("访问 http://localhost:5000 使用前端界面")
    
    app.run(debug=True, host='0.0.0.0', port=8000)