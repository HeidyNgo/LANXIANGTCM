import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from datetime import date # Thêm thư viện để lấy ngày hiện tại

# --- CẤU HÌNH ---
# Code MỚI: Đọc key từ biến môi trường trên server Render
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# --- KHỞI TẠO ỨNG DỤNG ---
os.makedirs('templates', exist_ok=True)
app = Flask(__name__)

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_tcm_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    customer_name = data.get("Customer Name")
    time_reason = data.get("Time and Reason")
    symptoms = data.get("Symptoms")
    treatment_method = data.get("Treatment Method")
    session_num = data.get("n")
    total_sessions = data.get("total")

    # Lấy ngày hiện tại làm ngày khám
    consultation_date = date.today().strftime("%B %d, %Y")

    # --- PROMPT MỚI, RÕ RÀNG HƠN CHO AI ---
    prompt = f"""
    You are a medical assistant at a Traditional Chinese Medicine (TCM) clinic. Your task is to write a professional patient case record in English based on the provided data.

    **Today's Date (Date of Consultation):** {consultation_date}

    **Patient Information to be used in the record:**
    - Patient Name: {customer_name}
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
        return jsonify({"ai_generated_report": ai_response.strip()})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- CHẠY APP ---
if __name__ == '__main__':
    app.run(debug=True)
