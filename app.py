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

# 모델명을 가장 빠르고 안정적인 최신 1.5-flash로 고정합니다.
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    # 🚀 [업그레이드 완료] G마켓/쇼핑몰 할인가 및 수량 완벽 인식 프롬프트
    prompt = """
    [역할: 대한민국 학교 행정실무사 및 데이터 검증 전문가]
    너는 초등학교 품의서 작성을 위해 각종 증빙 자료(텍스트, 엑셀, 이미지, PDF)를 완벽하게 분석하는 전문가야. 
    사용자가 제시한 자료에서 '품명', '수량', '최종 결제 금액'을 추출하여 보고해.

    [데이터 추출 및 정제 핵심 규칙 - 반드시 지킬 것!]
    1. 단가(Price) 결정 규칙 (가장 중요): 
       - '공급가액', '정가'를 절대 단가로 쓰지 마.
       - 할인이 적용된 **'최종 결제 금액(할인 적용 후 단가)'**을 반드시 단가로 추출해.
       - 만약 단가와 수량을 곱했을 때 합계와 맞지 않으면, 품목별 최종 합계를 수량으로 나눈 값을 단가로 써.
    2. 상품명 필터링: 
       - 상품명 앞뒤의 [특가], (무료배송), [정품], [G마켓/쇼핑몰], '쿠폰적용가' 같은 광고성 수식어는 100% 삭제해. 
       - 핵심 상품명만 남겨라. (예: "3M 정전기 청소포 100매")
    3. 수량(Qty): 
       - 숫자만 추출해. '4개'라면 '4'만 남겨. 묶음 상품의 이름에 적힌 숫자에 속지 말고 '실제 주문 수량'을 가져와.
    4. 무시할 항목: 
       - 배송비, 포인트 결제, 전체 총 합계(Total) 줄은 절대 개별 품목으로 추출하지 마.

    [응답 형식]
    - 반드시 아래와 같은 '순수 JSON 배열' 형식으로만 응답하라. 코드 블록(```)이나 다른 설명은 절대 추가하지 마.
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