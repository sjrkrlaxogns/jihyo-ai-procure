from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import json

app = Flask(__name__)

# 1. 제미나이 API 세팅 (부장님의 API 키를 꼭 넣어주세요!)
API_KEY = "AIzaSyBGH5yhDDFQYcCTpscmMfHYksLdhsldLwQ"
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
        # [부장님 지적사항 반영] 초정밀 검증형 프롬프트
        prompt = """
        [역할: 대한민국 학교 행정 전용 데이터 정제 전문가]
        너는 이미지, PDF, 엑셀 자료를 분석하여 품의서용 도서 목록을 추출하는 전문가야. 
        데이터 추출 시 아래 [필수 검증 규칙]을 100% 준수하여 오차를 없애라.

        [필수 검증 규칙]
        1. **긴 제목 줄바꿈 통합**: 
           - 책 제목이 길어서 두 줄 이상으로 나뉘어 있는 경우, 이를 절대 별개의 품목으로 나누지 마라. 
           - 문맥을 파악하여 하나의 도서명으로 반드시 합쳐서 한 줄로 표기하라.
        
        2. **합계 및 부가정보 제외 (금액 뻥튀기 방지)**: 
           - '합계', '총액', '배송비', '할인액', '포인트' 등이 적힌 줄은 상품이 아니다. 절대 리스트에 넣지 마라.
           - 리스트의 마지막에 나타나는 '총 결제 금액'을 상품으로 오인하여 추가하면 금액이 2배가 되니 주의하라.
        
        3. **중복 데이터 제거**: 
           - 이미지 내에 상세 내역과 요약 내역이 동시에 존재할 경우, 상세 내역에서 딱 한 번만 추출하라.
           - 동일한 금액이 반복 보인다면 중복 여부를 반드시 체크하라.

        4. **상품명 정제**: 
           - '무료배송', '특가', '정품', '쿠폰' 등의 수식어는 삭제하고 순수 도서명/물품명만 남겨라.

        [응답 형식]
        - 반드시 아래와 같은 '순수 JSON 배열' 형식으로만 응답하라. (설명 금지)
        [
          {"name": "정확한 도서명", "qty": 1, "price": 15000}
        ]
        """
        
        # 파일 형식에 따른 분석 실행
        if ext in ['xls', 'xlsx', 'csv']:
            try:
                with open(filepath, 'r', encoding='utf-8') as f: file_text = f.read()
            except:
                with open(filepath, 'r', encoding='cp949') as f: file_text = f.read()
            response = model.generate_content(prompt + f"\n\n[데이터 원본]\n{file_text}")
        elif ext in ['jpg', 'jpeg', 'png', 'pdf']:
            uploaded_to_gemini = genai.upload_file(filepath)
            response = model.generate_content([prompt, uploaded_to_gemini])
            genai.delete_file(uploaded_to_gemini.name)
        else:
            os.remove(filepath)
            return jsonify({"error": "지원하지 않는 파일 형식입니다."}), 400
        
        # AI 응답 텍스트 정제
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        result_data = json.loads(clean_text)
        
        # [이중 방어막] 파이썬 코드로 한 번 더 거르기 (합계 줄 강제 삭제)
        final_list = []
        forbidden_words = ['합계', '총액', '총금액', '배송비', '총계', '결제금액', '할인액']
        
        for item in result_data:
            # 이름에 금지어가 포함되어 있거나, 수량이 0이거나, 가격이 비정상적으로 크면 제외
            if any(word in item['name'] for word in forbidden_words):
                continue
            if item['qty'] < 1:
                continue
            final_list.append(item)
            
        os.remove(filepath)
        return jsonify(final_list) 
        
    except Exception as e:
        if os.path.exists(filepath): os.remove(filepath)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)