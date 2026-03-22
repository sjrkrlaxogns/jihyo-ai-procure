from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
import os
import json
import pandas as pd
import io
import base64

app = Flask(__name__)

# ★여기에 발급받으신 진짜 API 키를 그대로 유지해주세요!★
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
# 모델명을 안정적인 gemini-1.5-flash로 유지합니다.
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    prompt = """
    [역할: 대한민국 학교 행정실무사 및 데이터 검증 전문가]
    너는 초등학교 품의서 작성을 위해 각종 증빙 자료(텍스트, 엑셀, 이미지, PDF)를 완벽하게 분석하는 전문가야. 
    사용자가 제시한 자료에서 '품명', '수량', '최종 결제 금액'을 추출하여 보고해.

    [데이터 추출 및 정제 규칙]
    1. 상품명 필터링: '무료배송', '오늘출발', '정품', '특가', '쿠폰적용가' 등의 수식어는 100% 삭제하고 핵심 상품명만 남긴다.
    2. 중복 처리: 이미지 내 중복 데이터는 제거하고 '최종 판매가'가 적힌 항목 하나만 선택한다.
    3. 수량 및 단가: 수량은 숫자+단위 조합을 우선 찾고, 가격은 콤마 제거 후 숫자만 추출한다.
    4. 무시할 데이터: 배송비, 포인트, 합계 금액 줄은 제외한다.

    [응답 형식]
    - 반드시 아래와 같은 '순수 JSON 배열' 형식으로만 응답하라. 다른 설명은 금지한다.
    [
      {"name": "3M 정전기 청소포 대용량", "qty": 2, "price": 31000},
      {"name": "막대걸레 표준형", "qty": 1, "price": 15200}
    ]
    """
    
    content = [prompt]
    text_content = request.form.get('text', '')
    if text_content:
        content.append(f"\n\n[텍스트 내용]\n{text_content}")
        
    pasted_image = request.form.get('pasted_image')
    if pasted_image:
        img_data = base64.b64decode(pasted_image.split(',')[1])
        content.append({'mime_type': 'image/png', 'data': img_data})

    filepath = None
    uploaded_to_gemini = None
    
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        ext = file.filename.split('.')[-1].lower()
        filepath = f"temp_upload.{ext}"
        file.save(filepath)
        
        if ext in ['xls', 'xlsx', 'csv']:
            try:
                with open(filepath, 'r', encoding='utf-8') as f: file_text = f.read()
            except:
                with open(filepath, 'r', encoding='cp949') as f: file_text = f.read()
            content.append(f"\n\n[분석할 파일 데이터]\n{file_text}")
        elif ext in ['jpg', 'jpeg', 'png', 'pdf']:
            uploaded_to_gemini = genai.upload_file(filepath)
            content.append(uploaded_to_gemini)
        else:
            os.remove(filepath)
            return jsonify({"error": "지원하지 않는 파일 형식입니다."}), 400

    if len(content) == 1:
        return jsonify({"error": "분석할 데이터(파일 또는 텍스트)가 없습니다."}), 400

    try:
        response = model.generate_content(content)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        result_data = json.loads(clean_text)
        
        if filepath and os.path.exists(filepath): os.remove(filepath)
        if uploaded_to_gemini: genai.delete_file(uploaded_to_gemini.name)
            
        return jsonify(result_data) 
        
    except Exception as e:
        if filepath and os.path.exists(filepath): os.remove(filepath)
        if uploaded_to_gemini: 
            try: genai.delete_file(uploaded_to_gemini.name)
            except: pass
        return jsonify({"error": str(e)}), 500

# 🚀 [수정] 엑셀/에듀파인 호환성을 위한 UTF-8 (BOM 포함) CSV 다운로드
@app.route('/api/download_excel', methods=['POST'])
def download_excel():
    data = request.json
    items = data.get('items', [])
    
    df = pd.DataFrame(items)
    df_final = pd.DataFrame()
    df_final['내용'] = df['name']
    df_final['규격'] = ''
    df_final['단위'] = '개'
    df_final['수량'] = df['qty']
    df_final['예상단가'] = df['price']
    df_final['예상금액'] = df_final['수량'] * df_final['예상단가']
    
    # 메모리 버퍼에 CSV 쓰기
    output = io.BytesIO()
    # utf-8-sig 인코딩을 적용하여 엑셀에서도 한글이 바로 인식되게 함
    csv_string = df_final.to_csv(index=False, encoding='utf-8-sig')
    output.write(csv_string.encode('utf-8-sig'))
    output.seek(0)
    
    return send_file(output, 
                     mimetype='text/csv', 
                     as_attachment=True, 
                     download_name='지효초_품의목록_utf8.csv')

if __name__ == '__main__':
    app.run(debug=True, port=5000)





    