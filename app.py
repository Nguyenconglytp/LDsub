import os
import subprocess
# Thay thế import whisper bằng faster-whisper
from faster_whisper import WhisperModel
from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import time 
from deep_translator import GoogleTranslator
import re
import json
import threading
import uuid
from datetime import datetime

app = Flask(__name__)
# Use environment variable for secret key, fallback to a default for development
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure upload folder - use /tmp for ephemeral storage on Render.com
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Increase max file size to 500MB for Render.com (reduce from 2GB)
max_file_size = int(os.environ.get('MAX_FILE_SIZE', 500 * 1024 * 1024))  # 500MB default
app.config['MAX_CONTENT_LENGTH'] = max_file_size

# Global model variable for caching
whisper_model = None
current_model_size = None

def get_whisper_model(model_size="tiny"):
    """Get cached Whisper model or load if not exists"""
    global whisper_model, current_model_size
    if whisper_model is None or current_model_size != model_size:
        print(f"Đang tải mô hình Whisper {model_size}...")
        # Use faster-whisper model
        whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        current_model_size = model_size
        print("Mô hình Whisper đã sẵn sàng.")
    return whisper_model

# User database file
USERS_FILE = 'users.json'

# Helper functions for user management
def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def register_user(username, email, password):
    """Register a new user"""
    users = load_users()
    
    # Check if user already exists
    if username in users:
        return False, "Tên đăng nhập đã tồn tại"
    
    if email in [user['email'] for user in users.values()]:
        return False, "Email đã được sử dụng"
    
    # Hash password and save user
    users[username] = {
        'email': email,
        'password': generate_password_hash(password),
        'created_at': time.time()
    }
    
    save_users(users)
    return True, "Đăng ký thành công"

def authenticate_user(username, password):
    """Authenticate user login"""
    users = load_users()
    
    if username in users:
        if check_password_hash(users[username]['password'], password):
            return True, "Đăng nhập thành công"
        else:
            return False, "Mật khẩu không đúng"
    else:
        return False, "Tên đăng nhập không tồn tại"

# Task tracking
tasks = {}

def format_time(seconds):
    """Định dạng giây thành chuỗi thời gian SRT: HH:MM:SS,ms"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def cleanup_files(file_paths):
    """Safely remove temporary files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not remove file {file_path}: {e}")

def generate_srt(result):
    """Tạo nội dung file SRT từ kết quả của Whisper"""
    srt_content = []
    for i, segment in enumerate(result['segments']):
        start_time = format_time(segment['start'])
        end_time = format_time(segment['end'])
        text = segment['text'].strip()
        
        srt_content.append(str(i + 1))
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("") # Dòng trống ngăn cách các phụ đề

    return "\n".join(srt_content)

def translate_srt_content(srt_content, src_lang, dest_lang):
    """Dịch nội dung SRT từ ngôn ngữ này sang ngôn ngữ khác"""
    # Map ngôn ngữ sang mã ngôn ngữ đúng cho Google Translate
    lang_map = {
        'zh': 'zh-CN',  # Chinese
        'zh-CN': 'zh-CN',
        'zh-TW': 'zh-TW',
        'jp': 'ja',     # Japanese
        'kr': 'ko',     # Korean
        'vn': 'vi',     # Vietnamese
    }
    
    # Áp dụng map nếu cần
    src_lang = lang_map.get(src_lang, src_lang)
    dest_lang = lang_map.get(dest_lang, dest_lang)
    
    lines = srt_content.split('\n')
    translated_lines = []
    
    for line in lines:
        # Kiểm tra nếu dòng là nội dung phụ đề (không phải số thứ tự, thời gian, hoặc dòng trống)
        if line and not line.isdigit() and '-->' not in line:
            try:
                # Dịch dòng này
                translator = GoogleTranslator(source=src_lang, target=dest_lang)
                translated = translator.translate(line)
                translated_lines.append(translated)
            except Exception as e:
                # Nếu dịch thất bại, giữ nguyên dòng gốc
                print(f"Lỗi dịch '{line}': {e}")
                translated_lines.append(line)
        else:
            # Giữ nguyên các dòng khác (số thứ tự, thời gian, dòng trống)
            translated_lines.append(line)
    
    return '\n'.join(translated_lines)

def burn_subtitles_to_video(video_path, srt_path, output_path, position='bottom', color='white'):
    """Thêm phụ đề vào video sử dụng FFmpeg"""
    # Map màu sắc sang mã màu
    color_map = {
        'white': 'white',
        'yellow': 'yellow',
        'red': 'red',
        'blue': 'blue',
        'green': 'green'
    }
    
    # Map vị trí sang tham số FFmpeg
    if position == 'top':
        position_param = 'x=(w-tw)/2:y=50'
    elif position == 'middle':
        position_param = 'x=(w-tw)/2:y=(h-th)/2'
    else:  # bottom
        position_param = 'x=(w-tw)/2:y=h-th-50'
    
    color_param = color_map.get(color, 'white')
    
    try:
        # Sử dụng FFmpeg để thêm phụ đề vào video
        # Note: This is a simplified approach. In practice, you might need to handle file paths differently on Windows
        command = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"subtitles={srt_path}:force_style='Fontsize=18,PrimaryColour=&HFFFFFF,Outline=1,Shadow=0,{position_param}'",
            '-c:a', 'copy',
            output_path
        ]
        
        # For Windows, we might need to adjust the path format
        if os.name == 'nt':  # Windows
            srt_path_windows = srt_path.replace('\\', '\\\\').replace(':', '\\:').replace(',', '\\,')
            command = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f"subtitles={srt_path_windows}:force_style='Fontsize=18,PrimaryColour=&HFFFFFF,Outline=1,Shadow=0,{position_param}'",
                '-c:a', 'copy',
                output_path
            ]
        
        subprocess.run(command, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi thêm phụ đề vào video: {e}")
        return False

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', logged_in=True, username=session['username'])
    return render_template('index.html', logged_in=False)

@app.route('/health')
def health_check():
    """Health check endpoint for Render.com"""
    return jsonify({
        "status": "healthy",
        "service": "LDsub", 
        "version": "1.0.0"
    }), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        success, message = authenticate_user(username, password)
        
        if success:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error=message)
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate input
        if not username or not email or not password:
            return render_template('register.html', error="Vui lòng điền đầy đủ thông tin")
        
        if password != confirm_password:
            return render_template('register.html', error="Mật khẩu xác nhận không khớp")
        
        if len(password) < 6:
            return render_template('register.html', error="Mật khẩu phải có ít nhất 6 ký tự")
        
        success, message = register_user(username, email, password)
        
        if success:
            return redirect(url_for('login'))
        else:
            return render_template('register.html', error=message)
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/transcribe', methods=['POST'])
def transcribe_video():
    try:
        # Check if user is logged in
        if 'username' not in session:
            return jsonify({"error": "Vui lòng đăng nhập để sử dụng tính năng này"}), 401

        if 'video' not in request.files:
            return jsonify({"error": "Không tìm thấy file video"}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({"error": "Chưa chọn file"}), 400

        language = request.form.get('language', 'vi')
        accuracy = request.form.get('accuracy', 'base')

        if file:
            # Save the file first before starting background processing
            timestamp = str(int(time.time()))
            filename = secure_filename(file.filename)
            base_filename, file_extension = os.path.splitext(filename)
            unique_filename = f"{base_filename}_{timestamp}"
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_filename}{file_extension}")
            
            # Save the file immediately
            file.save(video_path)
            
            # Create a unique task ID
            task_id = str(uuid.uuid4())
            
            # Store task info
            tasks[task_id] = {
                'status': 'processing',
                'progress': 0,
                'message': 'Đang bắt đầu xử lý...',
                'result': None,
                'error': None
            }
            
            # Start background processing with the saved file path
            thread = threading.Thread(
                target=transcribe_video_background,
                args=(task_id, video_path, base_filename, file_extension, language, accuracy)
            )
            thread.start()
            
            return jsonify({"task_id": task_id}), 202
    except Exception as e:
        # Ensure we always return JSON even in case of unexpected errors
        return jsonify({"error": f"Lỗi không xác định: {str(e)}"}), 500

def transcribe_video_background(task_id, video_path, base_filename, file_extension, language, accuracy):
    try:
        # Update task status
        tasks[task_id]['message'] = 'Đang bắt đầu xử lý...'
        
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_filename}.mp3")
        srt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_filename}.srt")

        tasks[task_id]['progress'] = 5
        tasks[task_id]['message'] = 'Đang trích xuất âm thanh...'

        # 1. Trích xuất âm thanh bằng FFmpeg
        try:
            # Optimized FFmpeg command with reduced quality for faster processing
            command = f'ffmpeg -i "{video_path}" -vn -ar 16000 -ac 1 -ab 64k -f mp3 "{audio_path}"'
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = f"Lỗi khi trích xuất âm thanh: {e}"
            return
        
        tasks[task_id]['progress'] = 25
        tasks[task_id]['message'] = 'Đã trích xuất âm thanh, đang chuyển giọng nói thành văn bản...'

        # 2. Chuyển giọng nói thành văn bản bằng Whisper
        try:
            model = get_whisper_model(accuracy)
            # Use faster-whisper transcription
            segments, info = model.transcribe(audio_path, language=language, beam_size=5)
            result = {
                "segments": [{"start": segment.start, "end": segment.end, "text": segment.text} for segment in segments],
                "language": info.language
            }
        except Exception as e:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = f"Lỗi khi chuyển giọng nói thành văn bản: {e}"
            return

        tasks[task_id]['progress'] = 75
        tasks[task_id]['message'] = 'Đã chuyển giọng nói thành văn bản, đang tạo file SRT...'

        # 3. Tạo file SRT
        srt_data = generate_srt(result)
        with open(srt_path, 'w', encoding='utf-8') as srt_file:
            srt_file.write(srt_data)
            
        tasks[task_id]['progress'] = 90
        tasks[task_id]['message'] = 'Đã tạo file SRT, đang hoàn tất...'

        # 4. Update task with result
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['result'] = {
            'srt_path': srt_path,
            'filename': f"{base_filename}.srt"
        }
        tasks[task_id]['progress'] = 100
        tasks[task_id]['message'] = 'Hoàn thành!'
        
        # Clean up temporary files (optional)
        # os.remove(video_path)
        # os.remove(audio_path)
        
    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = f"Lỗi không xác định: {str(e)}"

@app.route('/task_status/<task_id>')
def task_status(task_id):
    if task_id in tasks:
        task = tasks[task_id]
        return jsonify(task)
    else:
        return jsonify({'status': 'not_found', 'error': 'Task not found'}), 404

@app.route('/download_srt/<task_id>')
def download_srt(task_id):
    if task_id in tasks and tasks[task_id]['status'] == 'completed':
        result = tasks[task_id]['result']
        # Clean up temporary files after download
        temp_files = result.get('temp_files', [])
        response = send_file(result['srt_path'], as_attachment=True, download_name=result['filename'])
        # Clean up temp files after sending
        cleanup_files(temp_files)
        return response
    else:
        return jsonify({'error': 'File not found or task not completed'}), 404

@app.route('/translate', methods=['POST'])
def translate_srt():
    try:
        # Check if user is logged in
        if 'username' not in session:
            return jsonify({"error": "Vui lòng đăng nhập để sử dụng tính năng này"}), 401

        if 'srt' not in request.files:
            return jsonify({"error": "Không tìm thấy file SRT"}), 400

        file = request.files['srt']
        if file.filename == '':
            return jsonify({"error": "Chưa chọn file"}), 400

        from_lang = request.form.get('from_lang', 'vi')
        to_lang = request.form.get('to_lang', 'en')

        if file:
            # Tạo tên file độc nhất
            timestamp = str(int(time.time()))
            filename = secure_filename(file.filename)
            base_filename, file_extension = os.path.splitext(filename)
            unique_filename = f"{base_filename}_translated_{timestamp}"
            srt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_filename}.srt")

            # Lưu file tạm
            file.save(srt_path)

            # Đọc nội dung file SRT
            try:
                with open(srt_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
            except Exception as e:
                return jsonify({"error": f"Lỗi khi đọc file SRT: {e}"}), 500

            # Dịch nội dung SRT
            try:
                translated_content = translate_srt_content(srt_content, from_lang, to_lang)
            except Exception as e:
                return jsonify({"error": f"Lỗi khi dịch phụ đề: {e}"}), 500

            # Ghi nội dung đã dịch vào file mới
            translated_srt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_filename}_translated.srt")
            with open(translated_srt_path, 'w', encoding='utf-8') as f:
                f.write(translated_content)

            # Xóa file tạm
            os.remove(srt_path)

            # Trả file SRT đã dịch về cho người dùng
            return send_file(translated_srt_path, as_attachment=True, download_name=f"{base_filename}_translated.srt")

        return jsonify({"error": "Lỗi không xác định"}), 500
    except Exception as e:
        # Ensure we always return JSON even in case of unexpected errors
        return jsonify({"error": f"Lỗi không xác định: {str(e)}"}), 500

@app.route('/burn', methods=['POST'])
def burn_subtitles():
    try:
        # Check if user is logged in
        if 'username' not in session:
            return jsonify({"error": "Vui lòng đăng nhập để sử dụng tính năng này"}), 401

        if 'video' not in request.files or 'srt' not in request.files:
            return jsonify({"error": "Thiếu file video hoặc file SRT"}), 400

        video_file = request.files['video']
        srt_file = request.files['srt']
        
        if video_file.filename == '' or srt_file.filename == '':
            return jsonify({"error": "Chưa chọn file"}), 400

        position = request.form.get('position', 'bottom')
        color = request.form.get('color', 'white')

        if video_file and srt_file:
            # Tạo tên file độc nhất
            timestamp = str(int(time.time()))
            
            # Xử lý video
            video_filename = secure_filename(video_file.filename)
            video_base_filename, video_extension = os.path.splitext(video_filename)
            unique_video_filename = f"{video_base_filename}_{timestamp}"
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_video_filename}{video_extension}")
            video_file.save(video_path)
            
            # Xử lý SRT
            srt_filename = secure_filename(srt_file.filename)
            srt_base_filename, srt_extension = os.path.splitext(srt_filename)
            unique_srt_filename = f"{srt_base_filename}_{timestamp}"
            srt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_srt_filename}{srt_extension}")
            srt_file.save(srt_path)
            
            # Đường dẫn file output
            output_filename = f"{video_base_filename}_with_subtitles_{timestamp}{video_extension}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

            # Thêm phụ đề vào video
            success = burn_subtitles_to_video(video_path, srt_path, output_path, position, color)
            
            if not success:
                # Dọn dẹp file tạm
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(srt_path):
                    os.remove(srt_path)
                return jsonify({"error": "Lỗi khi thêm phụ đề vào video. Đảm bảo FFmpeg đã được cài đặt."}), 500

            # Dọn dẹp file tạm
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(srt_path):
                os.remove(srt_path)

            # Trả video đã thêm phụ đề về cho người dùng
            return send_file(output_path, as_attachment=True, download_name=output_filename)

        return jsonify({"error": "Lỗi không xác định"}), 500
    except Exception as e:
        # Ensure we always return JSON even in case of unexpected errors
        return jsonify({"error": f"Lỗi không xác định: {str(e)}"}), 500

if __name__ == '__main__':
    # Get port from environment variable (Render.com sets this)
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 for external access on Render.com
    app.run(host='0.0.0.0', port=port, debug=False)