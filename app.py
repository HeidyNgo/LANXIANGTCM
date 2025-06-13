import os
import io
from flask import Flask, request, jsonify, render_template, Response, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from urllib.parse import quote
from collections import defaultdict
from reportlab.pdfgen import canvas
import google.generativeai as genai

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# Sửa URL PostgreSQL cho SQLAlchemy nếu cần
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---
class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient_name = db.Column(db.String(150), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    ai_report = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# --- ROUTES ---
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
    You are a medical assistant at a Traditional Chinese Medicine (TCM) clinic. Your task is to write a professional patient case record in English based on the provided data.

    **Today's Date (Date of Consultation):** {consultation_date}
    **Patient Name:** {patient_name}
    **Onset and Cause of Condition:** {time_reason}
    **Presenting Symptoms:** {symptoms}
    **Treatment This Session:** {treatment_method}
    **Treatment Course:** Session {session_num} of {total_sessions}

    Please generate a structured report with sections like:
    - Patient History
    - Diagnosis (TCM)
    - Treatment Protocol
    - Prognosis
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
    all_records = db.session.execute(db.select(Record).order_by(Record.created_at.desc())).scalars().all()
    return render_template('history.html', records=all_records)

@app.route('/download/<int:record_id>')
def download_record(record_id):
    record = db.get_or_404(Record, record_id)

    file_content = f"HỒ SƠ BỆNH ÁN #{record.id}\n"
    file_content += f"Tên bệnh nhân: {record.patient_name}\n"
    file_content += f"Ngày tạo: {record.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    file_content += f"Triệu chứng đã khai:\n{record.symptoms}\n\n"
    file_content += f"Phương pháp điều trị:\n{record.treatment}\n\n"
    file_content += f"BÁO CÁO TỪ AI:\n{record.ai_report}"

    filename = f"{record.created_at.strftime('%Y-%m-%d')}_{record.id}_{record.patient_name.replace(' ', '_')}.txt"
    return Response(
        file_content.encode('utf-8'),
        mimetype="text/plain; charset=utf-8",
        headers={"Content-disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )

@app.route('/download_pdf/<int:record_id>')
def download_pdf(record_id):
    record = db.get_or_404(Record, record_id)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    y = 800

    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, f"📄 HỒ SƠ BỆNH ÁN #{record.id}")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(100, y, f"Tên bệnh nhân: {record.patient_name}")
    y -= 20
    p.drawString(100, y, f"Ngày tạo: {record.created_at.strftime('%d/%m/%Y')}")
    y -= 30

    p.drawString(100, y, "🔸 Triệu chứng:")
    y -= 20
    for line in record.symptoms.splitlines():
        p.drawString(110, y, line)
        y -= 15

    y -= 10
    p.drawString(100, y, "🔸 Phương pháp điều trị:")
    y -= 20
    for line in record.treatment.splitlines():
        p.drawString(110, y, line)
        y -= 15

    y -= 10
    p.drawString(100, y, "🤖 Báo cáo từ AI:")
    y -= 20
    for line in record.ai_report.splitlines():
        p.drawString(110, y, line)
        y -= 15
        if y < 50:
            p.showPage()
            y = 800

    p.save()
    buffer.seek(0)

    filename = f"hoso_{record.id}_{record.patient_name.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/delete_record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    correct_password = "1234"
    submitted_password = request.form.get('password')

    if submitted_password != correct_password:
        return "Mật khẩu không đúng. Không thể xóa hồ sơ.", 403

    record = db.get_or_404(Record, record_id)
    try:
        db.session.delete(record)
        db.session.commit()
        return redirect(url_for('history'))
    except Exception as e:
        db.session.rollback()
        return f"Có lỗi xảy ra: {e}", 500

# --- CHẠY APP ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
