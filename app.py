import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy # Thư viện mới giúp làm việc với database dễ hơn
from datetime import datetime

# --- CẤU HÌNH ---
# Lấy các biến môi trường đã cài đặt trên Render
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Cấu hình AI
genai.configure(api_key=GEMINI_API_KEY)

# --- KHỞI TẠO ỨNG DỤNG VÀ DATABASE ---
app = Flask(__name__)
# Cung cấp địa chỉ database cho ứng dụng
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Khởi tạo đối tượng database
db = SQLAlchemy(app)

# Định nghĩa cấu trúc của bảng 'records' bằng một class Python
class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient_name = db.Column(db.String(100), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    ai_report = db.Column(db.Text, nullable=False)

# Tạo tất cả các bảng trong database (nếu chúng chưa tồn tại)
with app.app_context():
    db.create_all()

# --- CÁC ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_tcm_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    patient_name = data.get("Patient Name")
    time_reason = data.get("Time and Reason")
    symptoms = data.get("Symptoms")
    treatment_method = data.get("Treatment Administered")
    session_num = data.get("Current Treatment Session Number")
    total_sessions = data.get("Planned Total Sessions")
    
    consultation_date = datetime.now().strftime("%B %d, %Y")

    prompt = f"""
    You are a medical assistant... (Toàn bộ prompt của bạn giữ nguyên ở đây)
    ...
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        ai_response = response.text

        # --- LƯU VÀO DATABASE BẰNG CÁCH MỚI ---
        new_record = Record(
            patient_name=patient_name,
            symptoms=symptoms,
            treatment=treatment_method,
            ai_report=ai_response
        )
        db.session.add(new_record)
        db.session.commit()
        print("Một hồ sơ mới đã được lưu vào database PostgreSQL.")

        return jsonify({"ai_generated_report": ai_response.strip()})
    
    except Exception as e:
        db.session.rollback() # Hoàn tác nếu có lỗi
        return jsonify({"error": str(e)}), 500

@app.route('/history')
def history():
    # Đọc từ database bằng cách mới
    all_records = Record.query.order_by(Record.created_at.desc()).all()
    return render_template('history.html', records=all_records)

# --- CHẠY APP ---
if __name__ == '__main__':
    app.run(debug=True)
