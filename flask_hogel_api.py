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
import uuid
import hogel_processing

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
APP_PORT = 8000

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


def get_task_upload_dir(task_id):
    safe_task_id = secure_filename(task_id)
    return safe_task_id, os.path.join(app.config['UPLOAD_FOLDER'], safe_task_id)


def save_request_files_to_dir(files, target_dir):
    saved_files = []

    for index, file in enumerate(files, start=1):
        if not file or not allowed_file(file.filename):
            continue

        filename = secure_filename(file.filename)
        unique_filename = f"{index:03d}_{filename}"
        file_path = os.path.join(target_dir, unique_filename)
        file.save(file_path)
        saved_files.append(file_path)

    return saved_files


def prepare_input_files(temp_input_dir):
    task_id = request.form.get('taskId', type=str, default='').strip()
    if task_id:
        _, task_upload_dir = get_task_upload_dir(task_id)
        if not os.path.isdir(task_upload_dir):
            return jsonify({'success': False, 'error': f'任务不存在: {task_id}'}), 400

        copied_count = 0
        for filename in os.listdir(task_upload_dir):
            source_path = os.path.join(task_upload_dir, filename)
            if not os.path.isfile(source_path) or not allowed_file(filename):
                continue

            shutil.copy2(source_path, os.path.join(temp_input_dir, filename))
            copied_count += 1

        if copied_count == 0:
            return jsonify({'success': False, 'error': f'任务 {task_id} 下没有有效图像文件'}), 400

        return None

    if 'files' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'success': False, 'error': '没有选择文件'}), 400

    saved_files = save_request_files_to_dir(files, temp_input_dir)
    if not saved_files:
        return jsonify({'success': False, 'error': '没有有效的图像文件'}), 400

    return None


def get_task_output_dir(task_id):
    safe_task_id = secure_filename(task_id)
    return safe_task_id, os.path.join(app.config['OUTPUT_FOLDER'], safe_task_id)


def collect_generated_hogels(task_id, temp_output_dir, filename_prefix):
    safe_task_id, task_output_dir = get_task_output_dir(task_id)
    os.makedirs(task_output_dir, exist_ok=True)

    hogel_files = [f for f in os.listdir(temp_output_dir) if f.lower().endswith('.jpg')]
    hogel_files.sort()

    hogels = []
    for hogel_file in hogel_files:
        hogel_path = os.path.join(temp_output_dir, hogel_file)

        preview_url = get_image_preview(hogel_path)
        file_size = os.path.getsize(hogel_path)

        output_filename = f"{filename_prefix}_{len(hogels) + 1:03d}.jpg"
        output_path = os.path.join(task_output_dir, output_filename)
        shutil.copy2(hogel_path, output_path)

        hogels.append({
            'name': output_filename,
            'size': f"{file_size / 1024:.1f} KB",
            'preview_url': preview_url,
            'download_url': f'/api/download/{safe_task_id}/{output_filename}'
        })

    download_all_url = f'/api/download-all/{safe_task_id}' if hogels else None
    return hogels, download_all_url


def resolve_generation_task_id():
    task_id = request.form.get('taskId', type=str, default='').strip()
    if task_id:
        return task_id
    return uuid.uuid4().hex


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
    if not files:
        return jsonify({'success': False, 'error': '没有选择文件'}), 400

    requested_task_id = request.form.get('taskId', type=str, default='').strip()
    task_id = requested_task_id or uuid.uuid4().hex
    safe_task_id, task_upload_dir = get_task_upload_dir(task_id)
    if not safe_task_id:
        safe_task_id = uuid.uuid4().hex
        _, task_upload_dir = get_task_upload_dir(safe_task_id)

    os.makedirs(task_upload_dir, exist_ok=True)
    saved_files = save_request_files_to_dir(files, task_upload_dir)

    if not saved_files:
        return jsonify({'success': False, 'error': '没有有效的图像文件'}), 400

    uploaded_files = []
    for file_path in saved_files:
        preview_url = get_image_preview(file_path)
        file_size = os.path.getsize(file_path)

        uploaded_files.append({
            'filename': os.path.basename(file_path),
            'size': file_size,
            'preview_url': preview_url,
            'path': file_path
        })

    return jsonify({
        'success': True,
        'message': f'成功上传 {len(uploaded_files)} 个文件',
        'taskId': safe_task_id,
        'files': uploaded_files
    })

@app.route('/api/generate-hogel', methods=['POST'])
def generate_hogel():
    """生成hogel图像接口（水平视差）"""
    try:
        # 获取参数
        C = request.form.get('C', type=int, default=10)
        width = request.form.get('width', type=int, default=500)
        height = request.form.get('height', type=int, default=None)
        quality = request.form.get('quality', type=int, default=95)
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_input_dir:
            with tempfile.TemporaryDirectory() as temp_output_dir:
                prepare_error = prepare_input_files(temp_input_dir)
                if prepare_error:
                    return prepare_error
                
                # 使用新的处理模块
                try:
                    processor = hogel_processing.create_processor('horizontal')
                    processor.process(
                        input_folder=temp_input_dir,
                        output_folder=temp_output_dir,
                        C=C,
                        hogel_width_fixed=width,
                        hogel_height_fixed=height if height else None,
                        quality=quality
                    )
                    
                    process_log = "水平视差处理成功完成"
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'处理失败: {str(e)}'
                    }), 500
                
                task_id = resolve_generation_task_id()
                hogels, download_all_url = collect_generated_hogels(
                    task_id, temp_output_dir, 'hogel_horizontal'
                )

                return jsonify({
                    'success': True,
                    'message': f'成功生成 {len(hogels)} 个水平视差hogel图像',
                    'taskId': secure_filename(task_id),
                    'hogels': hogels,
                    'download_all_url': download_all_url,
                    'log': process_log
                })

    
    except Exception as e:
        print(f"生成hogel时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500

@app.route('/api/generate-full-parallax-hogel', methods=['POST'])
def generate_full_parallax_hogel():
    """生成全视差hogel图像接口"""
    try:
        # 获取参数
        canvas_width = request.form.get('canvas_width', type=float, default=100.0)
        canvas_height = request.form.get('canvas_height', type=float, default=100.0)
        exposure_width = request.form.get('exposure_width', type=float, default=10.0)
        quality = request.form.get('quality', type=int, default=95)
        
        # 参数验证
        if canvas_width <= 0 or canvas_height <= 0 or exposure_width <= 0:
            return jsonify({'success': False, 'error': '画幅尺寸和曝光宽度必须大于0'}), 400
        
        if exposure_width > canvas_width:
            return jsonify({'success': False, 'error': '曝光宽度不能大于画幅宽度'}), 400
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_input_dir:
            with tempfile.TemporaryDirectory() as temp_output_dir:
                prepare_error = prepare_input_files(temp_input_dir)
                if prepare_error:
                    return prepare_error
                
                # 使用新的处理模块
                try:
                    processor = hogel_processing.create_processor('full')
                    processor.process(
                        input_folder=temp_input_dir,
                        output_folder=temp_output_dir,
                        canvas_width=canvas_width,
                        canvas_height=canvas_height,
                        exposure_width=exposure_width,
                        quality=quality
                    )
                    
                    process_log = "全视差处理成功完成"
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'处理失败: {str(e)}'
                    }), 500
                
                task_id = resolve_generation_task_id()
                hogels, download_all_url = collect_generated_hogels(
                    task_id, temp_output_dir, 'hogel_full'
                )

                return jsonify({
                    'success': True,
                    'message': f'成功生成 {len(hogels)} 个全视差hogel图像',
                    'taskId': secure_filename(task_id),
                    'hogels': hogels,
                    'download_all_url': download_all_url,
                    'log': process_log
                })
    
    except Exception as e:
        print(f"生成全视差hogel时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500

@app.route('/api/download/<task_id>/<filename>', methods=['GET'])
def download_task_file(task_id, filename):
    """下载指定任务下的单个文件"""
    try:
        safe_task_id = secure_filename(task_id)
        safe_filename = secure_filename(filename)
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], safe_task_id, safe_filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """下载文件接口（兼容旧路径）"""
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], safe_filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def build_hogel_zip(source_dir, download_name):
    import zipfile
    from io import BytesIO

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in sorted(os.listdir(source_dir)):
            file_path = os.path.join(source_dir, filename)
            if os.path.isfile(file_path) and filename.lower().endswith('.jpg'):
                zf.write(file_path, filename)

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name
    )


@app.route('/api/download-all/<task_id>', methods=['GET'])
def download_all_for_task(task_id):
    """下载指定任务的全部hogel（zip）"""
    try:
        safe_task_id, task_output_dir = get_task_output_dir(task_id)
        if not safe_task_id or not os.path.isdir(task_output_dir):
            return jsonify({'success': False, 'error': f'任务不存在: {task_id}'}), 404

        return build_hogel_zip(task_output_dir, f'hogel_{safe_task_id}.zip')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download-all', methods=['GET'])
def download_all():
    """下载所有hogel文件（打包为zip，兼容旧路径）"""
    try:
        task_id = request.args.get('taskId', '').strip()
        if task_id:
            safe_task_id, task_output_dir = get_task_output_dir(task_id)
            if not safe_task_id or not os.path.isdir(task_output_dir):
                return jsonify({'success': False, 'error': f'任务不存在: {task_id}'}), 404
            return build_hogel_zip(task_output_dir, f'hogel_{safe_task_id}.zip')

        return build_hogel_zip(app.config['OUTPUT_FOLDER'], 'hogel_images.zip')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/clear-outputs', methods=['POST'])
def clear_outputs():
    """清空输出目录"""
    try:
        for entry in os.listdir(app.config['OUTPUT_FOLDER']):
            entry_path = os.path.join(app.config['OUTPUT_FOLDER'], entry)
            if os.path.isfile(entry_path):
                os.remove(entry_path)
            elif os.path.isdir(entry_path):
                shutil.rmtree(entry_path, ignore_errors=True)
        
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
            'horizontal': {
                'hogelCount': 10,
                'hogelWidth': 500,
                'heightMode': 'fixed',
                'hogelHeight': 500,
                'quality': 95,
                'enableAntiAliasing': True,
                'enableOptimization': True
            },
            'full': {
                'canvasWidth': 100.0,
                'canvasHeight': 100.0,
                'exposureWidth': 10.0,
                'quality': 95
            }
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
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('.', filename)

if __name__ == '__main__':
    print("启动 Hogel 图像生成器 API 服务...")
    print(f"上传目录: {UPLOAD_FOLDER}")
    print(f"输出目录: {OUTPUT_FOLDER}")
    print(f"访问 http://localhost:{APP_PORT} 使用前端界面")
    
    app.run(debug=True, host='0.0.0.0', port=APP_PORT)
