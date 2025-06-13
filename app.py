import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from urllib.parse import quote # Thư viện mới để xử lý tên file tiếng Việt
from itertools import groupby # Thư viện mới để gom nhóm theo ngày

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
genai.configure(api_key=GEMINI_API_KEY)

# --- KHỞI TẠO ỨNG DỤNG VÀ DATABASE ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient_name = db.Column(db.String(150), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    ai_report = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# --- CÁC ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_tcm_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    patient_name = data.get("Patient Name", "").title()
    time_reason = data.get("Time and Reason")
    symptoms = data.get("Symptoms")
    treatment_method = data.get("Treatment Method")
    session_num = data.get("Current Treatment Session Number")
    total_sessions = data.get("Planned Total Sessions")
    
    consultation_date = datetime.now().strftime("%B %d, %Y")

    prompt = f"""
    You are a medical assistant... (Toàn bộ prompt của bạn giữ nguyên ở đây) ...
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        ai_response = response.text

        new_record = Record(
            patient_name=patient_name,
            symptoms=symptoms,
            treatment=treatment_method,
            ai_report=ai_response
        )
        db.session.add(new_record)
        db.session.commit()
        return jsonify({"ai_generated_report": ai_response.strip()})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- ROUTE LỊCH SỬ ĐÃ ĐƯỢC NÂNG CẤP ---
@app.route('/history')
def history():
    all_records = db.session.execute(db.select(Record).order_by(Record.created_at.desc())).scalars().all()
    
    # Gom nhóm các bản ghi theo ngày tạo
    grouped_records = {}
    for key, group in groupby(all_records, key=lambda r: r.created_at.strftime('%Y-%m-%d')):
        grouped_records[key] = list(group)

    return render_template('history.html', grouped_records=grouped_records)

# --- ROUTE TẢI FILE ĐÃ ĐƯỢC SỬA LỖI ---
@app.route('/download/<int:record_id>')
def download_record(record_id):
    record = db.get_or_404(Record, record_id)
    
    file_content = f"HỒ SƠ BỆNH ÁN #{record.id}\n"
    file_content += f"================================\n\n"
    file_content += f"Tên bệnh nhân: {record.patient_name}\n"
    file_content += f"Ngày tạo (Giờ UTC): {record.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    file_content += f"Triệu chứng đã khai:\n{record.symptoms}\n\n"
    file_content += f"Phương pháp điều trị:\n{record.treatment}\n\n"
    file_content += f"--------------------------------\n"
    file_content += f"BÁO CÁO TỪ AI:\n"
    file_content += f"--------------------------------\n"
    file_content += record.ai_report

    filename_date = record.created_at.strftime('%Y-%m-%d')
    # Sửa lỗi tên file có tiếng Việt
    safe_patient_name = record.patient_name.replace(' ', '_')
    filename = f"{filename_date}_{record.id}_{safe_patient_name}.txt"
    encoded_filename = quote(filename)

    return Response(
        file_content.encode('utf-8'),
        mimetype="text/plain; charset=utf-8",
        headers={"Content-disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

# --- CHẠY APP ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
