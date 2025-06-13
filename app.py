import os
import sqlite3 # Giữ lại để init_database hoạt động trên máy local nếu cần
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
genai.configure(api_key=GEMINI_API_KEY)

# --- KHỞI TẠO ỨNG DỤNG VÀ DATABASE ---
app = Flask(__name__)
# Sửa lại để tương thích với PostgreSQL trên Render
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://", 1)
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

# Tạo tất cả các bảng trong database
with app.app_context():
    db.create_all()

# --- CÁC ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_tcm_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    # --- SỬA LỖI: Lấy đúng key từ JavaScript ---
    patient_name = data.get("Customer Name")
    time_reason = data.get("Time and Reason")
    symptoms = data.get("Symptoms")
    treatment_method = data.get("Treatment Method") # Đã sửa key
    session_num = data.get("Current Treatment Session Number")
    total_sessions = data.get("Planned Total Sessions")
    
    consultation_date = datetime.now().strftime("%B %d, %Y")

    # --- SỬA LỖI: PROMPT ĐẦY ĐỦ VÀ CHÍNH XÁC ---
    prompt = f"""
    You are a medical assistant at a Traditional Chinese Medicine (TCM) clinic. Your task is to write a professional patient case record in English based on the provided data.

    **Today's Date (Date of Consultation):** {consultation_date}

    **Patient Information to be used in the record:**
    - Patient Name: {patient_name}
    - Onset and Cause of Condition (When and how it started, as described by the patient): {time_reason}
    - Presenting Symptoms: {symptoms}
    - Treatment Administered This Session: {treatment_method}
    - Treatment Course: This is session number {session_num} of a planned {total_sessions}.

    **Instructions for AI:**
    1. Create a "Patient Case Record".
    2. Use "{consultation_date}" as the "Date of Initial Consultation".
    3. Use the "Onset and Cause of Condition" to write the "Patient History" section. Do not confuse this with the consultation date.
    4. Structure the report logically with clear headings like "Patient History", "Diagnosis (TCM)", "Treatment Protocol", and "Prognosis".
    5. Based on the symptoms, provide a plausible preliminary TCM diagnosis (e.g., Qi Stagnation, Blood Stasis, Damp-Heat, etc.).
    
    Please generate the professional case record now.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        ai_response = response.text

        # Lưu vào database bằng cách mới, đã sửa lỗi
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
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/history')
def history():
    # Sửa lại để tương thích với SQLAlchemy
    all_records = db.session.execute(db.select(Record).order_by(Record.created_at.desc())).scalars().all()
    return render_template('history.html', records=all_records)

# --- CHẠY APP ---
if __name__ == '__main__':
    app.run(debug=True)
