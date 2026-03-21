from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import json

app = Flask(__name__)

# 1. 제미나이 API 세팅 (본인의 키로 교체하세요)
API_KEY = "GEMINI_API_KEY"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({"error": "파일이 없습니다."}), 400
    
    file = request.files['file']
    ext = file.filename.split('.')[-1].lower()
    filepath = f"temp_upload.{ext}"
    file.save(filepath)
    
    try:
        # [끝판왕 프롬프트] 들여쓰기를 완벽하게 맞췄습니다.
        prompt = """
        [역할: 대한민국 학교 행정실무사 및 데이터 검증 전문가]
        너는 초등학교 품의서 작성을 위해 각종 증빙 자료(엑셀, 이미지, PDF)를 완벽하게 분석하는 전문가야. 
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
        
        if ext in ['xls', 'xlsx', 'csv']:
            try:
                with open(filepath, 'r', encoding='utf-8') as f: file_text = f.read()
            except:
                with open(filepath, 'r', encoding='cp949') as f: file_text = f.read()
            response = model.generate_content(prompt + f"\n\n[분석할 데이터]\n{file_text}")
        elif ext in ['jpg', 'jpeg', 'png', 'pdf']:
            uploaded_to_gemini = genai.upload_file(filepath)
            response = model.generate_content([prompt, uploaded_to_gemini])
            genai.delete_file(uploaded_to_gemini.name)
        else:
            os.remove(filepath)
            return jsonify({"error": "지원하지 않는 파일 형식입니다."}), 400
        
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        result_data = json.loads(clean_text)
        
        os.remove(filepath)
        return jsonify(result_data) 
        
    except Exception as e:
        if os.path.exists(filepath): os.remove(filepath)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)