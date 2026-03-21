from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
import os
import json
import pandas as pd
import io
import base64

app = Flask(__name__)

# Render 환경 변수 사용
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # 1. 파일 업로드 처리 (기존 방식)
    if 'file' in request.files:
        file = request.files['file']
        image_data = file.read()
        mime_type = file.mimetype
    # 2. 텍스트/붙여넣기 이미지 처리 (추가 방식)
    else:
        data = request.json
        text_content = data.get('text', '')
        pasted_image = data.get('image', None)
        
        if pasted_image:
            header, encoded = pasted_image.split(",", 1)
            image_data = base64.b64decode(encoded)
            mime_type = "image/png"
        else:
            image_data = None

    prompt = """
    물품 목록을 추출하여 JSON 배열로 응답하라. 
    형식: [{"name": "품명", "qty": 수량, "price": 단가}]
    배송비나 합계는 제외한다.
    """

    try:
        content = [prompt]
        if image_data:
            content.append({'mime_type': mime_type, 'data': image_data})
        if 'data' in locals() and data.get('text'):
            content.append(f"\n텍스트: {data.get('text')}")
            
        response = model.generate_content(content)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return jsonify(json.loads(clean_text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    items = data.get('items', [])
    df = pd.DataFrame(items)
    df.columns = ['내용', '수량', '예상단가']
    df['단위'] = '개'
    df['예상금액'] = df['수량'] * df['예상단가']
    df['규격'] = ''
    df = df[['내용', '규격', '단위', '수량', '예상단가', '예상금액']]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=True, index_label='순번')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='품의목록.xlsx')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)