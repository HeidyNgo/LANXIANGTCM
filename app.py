import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from urllib.parse import quote # Thư viện để xử lý tên file

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
genai.configure(api_key=GEMINI_API_KEY)

# --- KHỞI TẠO ỨNG DỤNG VÀ DATABASE ---
app = Flask(__name__)
# Sửa lại chuỗi kết nối để tương thích với SQLAlchemy trên Render
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Định nghĩa cấu trúc của bảng 'records'
class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient_name = db.Column(db.String(150), nullable=False)
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
    # Tự động viết hoa chữ cái đầu của tên
    patient_name = data.get("Patient Name", "").title()
    time_reason = data.get("Time and Reason")
    symptoms = data.get("Symptoms")
    treatment_method = data.get("Treatment Method")
    session_num = data.get("Current Treatment Session Number")
    total_sessions = data.get("Planned Total Sessions")
    
    consultation_date = datetime.now().strftime("%B %d, %Y")

    # Prompt đầy đủ cho AI
    prompt = f"""
    You are a medical assistant at a Traditional Chinese Medicine (TCM) clinic. Your task is to write a professional patient case record in English based on the provided data.
    Today's Date (Date of Consultation): {consultation_date}
    Patient Information to be used in the record:
    - Patient Name: {patient_name}
    - Onset and Cause of Condition (When and how it started, as described by the patient): {time_reason}
    - Presenting Symptoms: {symptoms}
    - Treatment Administered This Session: {treatment_method}
    - Treatment Course: This is session number {session_num} of a planned {total_sessions}.
    Instructions for AI:
    1. Create a "Patient Case Record".
    2. Use "{consultation_date}" as the "Date of Initial Consultation".
    3. Use the "Onset and Cause of Condition" to write the "Patient History" section.
    4. Structure the report logically with clear headings like "Patient History", "Diagnosis (TCM)", "Treatment Protocol", and "Prognosis".
    5. Based on the symptoms, provide a plausible preliminary TCM diagnosis.
    Please generate the professional case record now.
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

@app.route('/history')
def history():
    # Code này không cần chuyển đổi múi giờ, JavaScript sẽ làm việc đó
    all_records = db.session.execute(db.select(Record).order_by(Record.created_at.desc())).scalars().all()
    return render_template('history.html', records=all_records)

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
