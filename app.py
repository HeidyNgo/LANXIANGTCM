import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# --- CẤU HÌNH ---
# Code MỚI: Đọc key từ biến môi trường trên server Render
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)


# --- KHỞI TẠO ỨNG DỤNG ---
os.makedirs('templates', exist_ok=True)
app = Flask(__name__)


# --- CÁC ROUTES ---

# Route 1: Hiển thị trang web cho người dùng
@app.route('/')
def index():
    return render_template('index.html')


# Route 2: API để AI xử lý dữ liệu
@app.route('/generate_tcm_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    customer_name = data.get("Customer Name")
    time_reason = data.get("Time and Reason")
    symptoms = data.get("Symptoms")
    treatment_method = data.get("Treatment Method")
    session_num = data.get("n")
    total_sessions = data.get("total")

    prompt = f"""
    Based on the following patient information from a Traditional Chinese Medicine (TCM) clinic, please write a professional medical case record in English.
    The tone should be clinical, objective, and concise. Structure it logically with clear headings like "Patient History", "Diagnosis", "Treatment Protocol", and "Prognosis".

    Patient Information:
    - Name: {customer_name}
    - Onset and Cause: {time_reason}
    - Presenting Symptoms: {symptoms}
    - Treatment Administered: {treatment_method}
    - Treatment Course: This is session number {session_num} out of a planned {total_sessions} sessions.
    Please generate the case record now.
    """
    # Khối try...except đã được thụt dòng chính xác
    try:
        # Dòng model đã được sửa lại
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        ai_response = response.text
        return jsonify({"ai_generated_report": ai_response.strip()})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- CHẠY APP ---
if __name__ == '__main__':
    app.run(debug=True)
