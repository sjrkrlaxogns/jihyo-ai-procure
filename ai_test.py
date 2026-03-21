import google.generativeai as genai
import pandas as pd

# 1. API 키 설정 (아까 발급받은 키를 꼭 다시 넣어주세요!)
genai.configure(api_key="AIzaSyBGH5yhDDFQYcCTpscmMfHYksLdhsldLwQ")

model = genai.GenerativeModel('gemini-2.5-flash')

print("파일을 읽고 있습니다...")

# 2. 진짜 엑셀인지 가짜 엑셀(HTML)인지 눈치껏 읽어오기
try:
    # 먼저 진짜 엑셀이라고 믿고 읽어보기
    df = pd.read_excel('Estimation.xls') 
    file_text = df.to_string()
except:
    # 에러가 나면(가짜 엑셀이면) 당황하지 않고 텍스트 파일처럼 통째로 읽기
    print("💡 쇼핑몰용 가짜 엑셀(HTML) 파일로 감지되어 텍스트로 바로 읽어옵니다.")
    try:
        # 요즘 사이트 방식 (UTF-8)
        with open('Estimation.xls', 'r', encoding='utf-8') as f:
            file_text = f.read()
    except UnicodeDecodeError:
        # 옛날 쇼핑몰 방식 (CP949/EUC-KR)
        with open('Estimation.xls', 'r', encoding='cp949') as f:
            file_text = f.read()

# 3. AI 프롬프트 작성
prompt = f"""
너는 학교 행정실무사야. 아래 복잡한 데이터(또는 HTML 코드) 속에서 '품명(도서명)', '수량', '단가(할인금액이 아닌 진짜 결제금액)'만 정확히 추출해줘.
결과는 반드시 아래와 같은 탭(\\t) 형태의 텍스트로만 대답해. 다른 인사말이나 설명은 절대 금지야.

[출력 양식 예시]
진짜 진짜 재밌는 곤충 그림책\t1\t20700
흰 눈(빅북)\t1\t54000

[분석할 데이터]
{file_text}
"""

# 4. AI에게 질문하기
print("AI(Gemini)가 데이터를 분석 중입니다. 잠시만 기다려주세요... ⏳")
response = model.generate_content(prompt)

print("\n🎉 [AI 추출 결과] 🎉")
print(response.text)