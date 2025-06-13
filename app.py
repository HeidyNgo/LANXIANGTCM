import os
import sqlite3
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)


# --- KHỞI TẠO ỨNG DỤNG VÀ DATABASE ---
app = Flask(__name__)

def init_database():
    conn = sqlite3.connect('database.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            patient_name TEXT NOT NULL,
            symptoms TEXT NOT NULL,
            treatment TEXT NOT NULL,
            ai_report TEXT NOT NULL
        );
    ''')
    conn.close()
    print("Database đã được khởi tạo và sẵn sàng.")


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
    
    from datetime import date
    consultation_date = date.today().strftime("%B %d, %Y")

    # --- PROMPT ĐẦY ĐỦ VÀ CHÍNH XÁC ---
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

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO records (patient_name, symptoms, treatment, ai_report) VALUES (?, ?, ?, ?)",
                (patient_name, symptoms, treatment_method, ai_response)
            )
            conn.commit()
            conn.close()
            print("Một hồ sơ mới đã được lưu vào database.")
        except Exception as db_error:
            print(f"Lỗi khi lưu vào database: {db_error}")

        return jsonify({"ai_generated_report": ai_response.strip()})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/history')
def history():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    records = conn.execute('SELECT * FROM records ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('history.html', records=records)


# --- CHẠY APP ---
init_database()

if __name__ == '__main__':
    app.run(debug=True)
