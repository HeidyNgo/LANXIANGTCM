from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from urllib.parse import quote
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///records.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model
class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    symptoms = db.Column(db.Text, nullable=True)
    treatment = db.Column(db.Text, nullable=True)
    ai_report = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Home route (form input page)
@app.route('/')
def index():
    return render_template('index.html')

# Submit route
@app.route('/submit', methods=['POST'])
def submit():
    patient_name = request.form['patient_name']
    symptoms = request.form.get('symptoms', '')
    treatment = request.form.get('treatment', '')
    ai_report = request.form.get('ai_report', '')

    new_record = Record(
        patient_name=patient_name,
        symptoms=symptoms,
        treatment=treatment,
        ai_report=ai_report
    )
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('history'))

# History route
@app.route('/history')
def history():
    records = Record.query.order_by(Record.created_at.desc()).all()
    return render_template('history.html', records=records)

# Download PDF route
@app.route('/download/<int:record_id>')
def download_record(record_id):
    record = db.get_or_404(Record, record_id)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Font supports Vietnamese characters
    font_path = "DejaVuSans.ttf"
    if not os.path.isfile(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", font_path))
    p.setFont("DejaVu", 12)

    text = p.beginText(50, 750)
    lines = [
        f"TCM Patient Record #{record.id}",
        "===============================",
        f"Patient Name: {record.patient_name}",
        f"Created At: {record.created_at.strftime('%Y-%m-%d')}",
        "",
        "Symptoms Reported:",
        record.symptoms or "",
        "",
        "Treatment Method:",
        record.treatment or "",
        "",
        "--------------------------------",
        "AI-Generated Report:",
        "--------------------------------",
        record.ai_report or ""
    ]

    for line in lines:
        for l in line.split("\n"):
            text.textLine(l)

    p.drawText(text)
    p.showPage()
    p.save()
    buffer.seek(0)

    filename = f"{record.created_at.strftime('%Y-%m-%d')}_{record.id}_{record.patient_name.replace(' ', '_')}.pdf"
    encoded_filename = quote(filename)

    return Response(
        buffer,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    )

# Delete record with password
@app.route('/delete/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    password = request.form.get('password', '')
    if password == '1234':
        record = Record.query.get_or_404(record_id)
        db.session.delete(record)
        db.session.commit()
    return redirect(url_for('history'))

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

