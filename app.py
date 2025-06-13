from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pytz
import os
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///records.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_generated_report = db.Column(db.Text)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    report = request.form['report']
    new_record = Record(patient_name=name, ai_generated_report=report)
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('history'))

@app.route('/history')
def history():
    records = Record.query.order_by(Record.created_at.desc()).all()
    grouped = {}
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    for r in records:
        date = r.created_at.astimezone(tz).strftime('%Y-%m-%d')
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(r)
    return render_template('history.html', grouped_records=grouped)

@app.route('/download/<int:record_id>')
def download_pdf(record_id):
    record = Record.query.get_or_404(record_id)
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    created_date = record.created_at.astimezone(tz).strftime('%d/%m/%Y %H:%M:%S')

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # Đăng ký font hỗ trợ tiếng Việt
    font_path = os.path.join(os.path.dirname(__file__), 'DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('DejaVu', font_path))
    pdf.setFont('DejaVu', 14)

    pdf.drawString(50, 800, f"HỒ SƠ BỆNH ÁN #{record.id}")
    pdf.drawString(50, 780, "==============================")
    pdf.drawString(50, 760, f"Tên bệnh nhân: {record.patient_name}")
    pdf.drawString(50, 740, f"Ngày tạo: {created_date}")

    text_object = pdf.beginText(50, 700)
    text_object.setFont('DejaVu', 12)
    text_object.textLines(record.ai_generated_report)
    pdf.drawText(text_object)

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"record_{record.id}.pdf", mimetype='application/pdf')

@app.route('/delete_record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    correct_password = "1234"  # Mật khẩu xoá đúng
    submitted_password = request.form.get('password')
    if submitted_password != correct_password:
        return "Mật khẩu không đúng. Không thể xóa hồ sơ.", 403

    record = db.get_or_404(Record, record_id)
    try:
        db.session.delete(record)
        db.session.commit()
        return redirect(url_for('history'))
    except Exception:
        db.session.rollback()
        return "Có lỗi xảy ra khi xóa hồ sơ.", 500

if __name__ == '__main__':
    app.run(debug=True)
