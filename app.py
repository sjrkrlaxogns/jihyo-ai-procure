from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
import os
import json
import pandas as pd
import io
import base64

app = Flask(__name__)

# [보안] Render 환경 변수에서 키 가져오기
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # 속도를 위해 flash 사용

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    data = request.json
    text_content = data.get('text', '')
    image_data = data.get('image', None) # 붙여넣은 이미지(Base64)
    
    # [부장님 요청사항 반영] 초정밀 검증형 프롬프트
    prompt = """
    [역할: 대한민국 학교 행정 전문가]
    제시된 텍스트나 이미지에서 품의용 물품 목록을 추출하라.
    
    [규칙]
    1. 긴 제목은 하나로 합치고, '합계', '배송비' 등은 제외한다.
    2. 결과는 반드시 아래 JSON 배열 형식으로만 답하라.
    [{"name": "품명", "qty": 1, "price": 10000}]
    """

    try:
        content_to_send = [prompt]
        if text_content:
            content_to_send.append(f"\n[분석할 텍스트]\n{text_content}")
        
        if image_data:
            # Base64 이미지를 제미나이가 인식할 수 있는 형태로 변환
            header, encoded = image_data.split(",", 1)
            data = base64.b64decode(encoded)
            content_to_send.append({'mime_type': 'image/png', 'data': data})

        response = model.generate_content(content_to_send)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        result_data = json.loads(clean_text)
        
        # 중복 제거 및 정제
        final_list = [item for item in result_data if not any(word in item['name'] for word in ['합계', '총액', '배송비'])]
        
        return jsonify(final_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_excel():
    data = request.json
    items = data.get('items', [])
    
    # 엑셀 데이터 구성
    df = pd.DataFrame(items)
    df.columns = ['내용', '수량', '예상단가']
    df['단위'] = '개' # 기본값
    df['예상금액'] = df['수량'] * df['예상단가']
    df['규격'] = ''
    
    # 컬럼 순서 조정 (부장님 스크린샷 기준)
    df = df[['내용', '규격', '단위', '수량', '예상단가', '예상금액']]
    
    # 엑셀을 메모리에 생성
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=True, index_label='순번', sheet_name='품의목록')
    
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                     as_attachment=True, download_name='품의서_목록.xlsx')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)