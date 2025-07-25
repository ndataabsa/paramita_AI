"""
AI 모듈 - 정해진 질문과 답변 관리
실제 AI 연동 전 단계에서 사용하는 모의 AI 응답 시스템
"""

import re
import random
from typing import Dict, List, Optional, Tuple

class MockAI:
    def __init__(self):
        """정해진 질문/답변 패턴들을 초기화"""
        self.qa_patterns = self._load_qa_patterns()
        self.default_responses = self._load_default_responses()
        
    def _load_qa_patterns(self) -> List[Dict]:
        """정해진 질문/답변 패턴들"""
        return [
            # 🐍 Python 기초
            {
                "keywords": ["pandas", "csv", "데이터프레임", "데이터 읽기"],
                "question_pattern": r"(pandas|csv|데이터).*(읽|분석|처리)",
                "response": {
                    "content": """pandas를 사용한 CSV 데이터 분석 코드를 작성해드리겠습니다! 📊

다음은 기본적인 데이터 분석 워크플로우입니다:

1. **CSV 파일 읽기**
2. **데이터 기본 정보 확인**
3. **통계 요약 생성**
4. **시각화**

아래 코드를 실행해보세요!""",
                    "code_blocks": [
                        {
                            "id": "pandas_basic_analysis",
                            "language": "python",
                            "code": """import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# CSV 파일 읽기
df = pd.read_csv('data.csv')

# 데이터 기본 정보
print("=== 데이터 기본 정보 ===")
print(f"행 수: {len(df)}")
print(f"열 수: {len(df.columns)}")
print(f"컬럼명: {list(df.columns)}")

# 결측값 확인
print("\\n=== 결측값 확인 ===")
print(df.isnull().sum())

# 기술 통계
print("\\n=== 기술 통계 ===")
print(df.describe())

# 상위 5개 행 출력
print("\\n=== 데이터 미리보기 ===")
print(df.head())

# 간단한 히스토그램
plt.figure(figsize=(12, 8))
df.hist(bins=30)
plt.tight_layout()
plt.title('데이터 분포 히스토그램')
plt.show()"""
                        }
                    ]
                }
            },
            
            # 🕷️ 웹 스크래핑
            {
                "keywords": ["selenium", "크롤링", "스크래핑", "웹페이지"],
                "question_pattern": r"(selenium|크롤링|스크래핑).*(방법|코드)",
                "response": {
                    "content": """Selenium을 사용한 웹 스크래핑 코드를 작성해드리겠습니다! 🕷️

**주요 단계:**
1. **WebDriver 설정**
2. **페이지 로딩 대기**  
3. **요소 찾기 및 데이터 추출**
4. **안전한 종료**

동적 콘텐츠도 처리 가능한 코드입니다!""",
                    "code_blocks": [
                        {
                            "id": "selenium_scraping",
                            "language": "python", 
                            "code": """from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument('--headless')  # 브라우저 창 숨기기
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# WebDriver 초기화
driver = webdriver.Chrome(options=chrome_options)

try:
    # 웹페이지 이동
    url = "https://example.com"
    driver.get(url)
    
    # 페이지 로딩 대기
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    # 제목 추출
    title = driver.title
    print(f"페이지 제목: {title}")
    
    # 특정 요소들 찾기
    elements = driver.find_elements(By.CLASS_NAME, "content")
    
    # 데이터 추출
    scraped_data = []
    for element in elements:
        text = element.text.strip()
        if text:
            scraped_data.append(text)
            print(f"추출된 텍스트: {text}")
    
    print(f"\\n총 {len(scraped_data)}개의 데이터를 추출했습니다!")
    
except Exception as e:
    print(f"오류 발생: {str(e)}")
    
finally:
    # 브라우저 종료
    driver.quit()
    print("스크래핑 완료!")"""
                        }
                    ]
                }
            },
            
            # 🌐 Flask API
            {
                "keywords": ["flask", "api", "rest", "웹서버"],
                "question_pattern": r"(flask|api|rest).*(만들|개발|구현)",
                "response": {
                    "content": """Flask로 RESTful API를 구현하는 코드를 작성해드리겠습니다! 🌐

**API 엔드포인트:**
- `GET /api/users` - 사용자 목록 조회
- `POST /api/users` - 새 사용자 생성
- `GET /api/users/<id>` - 특정 사용자 조회
- `PUT /api/users/<id>` - 사용자 정보 수정
- `DELETE /api/users/<id>` - 사용자 삭제

완전한 CRUD API입니다!""",
                    "code_blocks": [
                        {
                            "id": "flask_api",
                            "language": "python",
                            "code": """from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# 메모리 내 데이터베이스 (실제로는 DB 사용)
users = [
    {"id": 1, "name": "김철수", "email": "kim@example.com", "created_at": "2024-01-01"},
    {"id": 2, "name": "이영희", "email": "lee@example.com", "created_at": "2024-01-02"}
]

# CORS 헤더 추가
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# 1. 모든 사용자 조회
@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({"success": True, "data": users, "count": len(users)})

# 2. 새 사용자 생성
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # 유효성 검사
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"success": False, "error": "name과 email이 필요합니다"}), 400
    
    # 새 사용자 생성
    new_user = {
        "id": max([u["id"] for u in users]) + 1 if users else 1,
        "name": data["name"],
        "email": data["email"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    users.append(new_user)
    return jsonify({"success": True, "data": new_user}), 201

# 3. 특정 사용자 조회
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"success": False, "error": "사용자를 찾을 수 없습니다"}), 404
    
    return jsonify({"success": True, "data": user})

# 4. 사용자 정보 수정
@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"success": False, "error": "사용자를 찾을 수 없습니다"}), 404
    
    data = request.get_json()
    if data:
        user.update({k: v for k, v in data.items() if k != "id"})
    
    return jsonify({"success": True, "data": user})

# 5. 사용자 삭제
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    global users
    users = [u for u in users if u["id"] != user_id]
    return jsonify({"success": True, "message": "사용자가 삭제되었습니다"})

if __name__ == '__main__':
    print("🌐 Flask API 서버 시작!")
    print("📋 사용 가능한 엔드포인트:")
    print("  GET    /api/users")
    print("  POST   /api/users")
    print("  GET    /api/users/<id>")
    print("  PUT    /api/users/<id>")
    print("  DELETE /api/users/<id>")
    
    app.run(debug=True, port=5000)"""
                        }
                    ]
                }
            },
            
            # 📊 데이터 시각화
            {
                "keywords": ["matplotlib", "시각화", "그래프", "차트"],
                "question_pattern": r"(matplotlib|시각화|그래프|차트).*(만들|그리|생성)",
                "response": {
                    "content": """matplotlib을 사용한 데이터 시각화 코드를 작성해드리겠습니다! 📊

**다양한 차트 유형:**
- **라인 차트** - 시간 변화 추이
- **바 차트** - 카테고리별 비교  
- **히스토그램** - 분포 확인
- **산점도** - 상관관계 분석
- **파이 차트** - 구성 비율

모든 차트에 한글 폰트 설정이 포함되어 있습니다!""",
                    "code_blocks": [
                        {
                            "id": "matplotlib_charts",
                            "language": "python",
                            "code": """import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 샘플 데이터 생성
months = ['1월', '2월', '3월', '4월', '5월', '6월']
sales = [120, 135, 148, 162, 158, 175]
expenses = [80, 85, 92, 98, 95, 105]

# 1. 라인 차트
plt.figure(figsize=(15, 12))

plt.subplot(2, 3, 1)
plt.plot(months, sales, marker='o', linewidth=2, label='매출')
plt.plot(months, expenses, marker='s', linewidth=2, label='비용')
plt.title('월별 매출/비용 추이', fontsize=14, fontweight='bold')
plt.legend()
plt.grid(True, alpha=0.3)

# 2. 바 차트
plt.subplot(2, 3, 2)
x = np.arange(len(months))
width = 0.35
plt.bar(x - width/2, sales, width, label='매출', alpha=0.8)
plt.bar(x + width/2, expenses, width, label='비용', alpha=0.8)
plt.title('월별 매출/비용 비교', fontsize=14, fontweight='bold')
plt.xticks(x, months)
plt.legend()

# 3. 히스토그램
plt.subplot(2, 3, 3)
data = np.random.normal(100, 15, 1000)
plt.hist(data, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
plt.title('데이터 분포 히스토그램', fontsize=14, fontweight='bold')
plt.xlabel('값')
plt.ylabel('빈도')

# 4. 산점도
plt.subplot(2, 3, 4)
x_data = np.random.randn(100)
y_data = 2 * x_data + np.random.randn(100)
plt.scatter(x_data, y_data, alpha=0.6, c='coral')
plt.title('상관관계 산점도', fontsize=14, fontweight='bold')
plt.xlabel('X 변수')
plt.ylabel('Y 변수')

# 5. 파이 차트
plt.subplot(2, 3, 5)
categories = ['카테고리A', '카테고리B', '카테고리C', '카테고리D']
values = [30, 25, 25, 20]
colors = ['gold', 'lightcoral', 'lightskyblue', 'lightgreen']
plt.pie(values, labels=categories, colors=colors, autopct='%1.1f%%', startangle=90)
plt.title('카테고리별 비율', fontsize=14, fontweight='bold')

# 6. 박스 플롯
plt.subplot(2, 3, 6)
data1 = np.random.normal(100, 10, 100)
data2 = np.random.normal(90, 20, 100)
data3 = np.random.normal(110, 5, 100)
plt.boxplot([data1, data2, data3], labels=['그룹A', '그룹B', '그룹C'])
plt.title('그룹별 박스 플롯', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.show()

print("🎨 다양한 차트가 생성되었습니다!")
print("📊 각 차트의 특징:")
print("  - 라인 차트: 시간에 따른 변화 추이")
print("  - 바 차트: 카테고리간 값 비교") 
print("  - 히스토그램: 데이터 분포 확인")
print("  - 산점도: 두 변수간 상관관계")
print("  - 파이 차트: 전체에서 각 부분의 비율")
print("  - 박스 플롯: 데이터의 분포와 이상치")"""
                        }
                    ]
                }
            }
        ]
    
    def _load_default_responses(self) -> List[str]:
        """기본 응답들"""
        return [
            "흥미로운 질문이네요! 🤔 좀 더 구체적으로 어떤 부분이 궁금하신지 알려주시면 더 정확한 도움을 드릴 수 있어요.",
            "죄송합니다, 해당 질문에 대한 준비된 답변이 없습니다. 다음과 같은 주제들에 대해서는 도움을 드릴 수 있어요:\n\n• Python 코딩 (pandas, matplotlib 등)\n• 웹 스크래핑 (Selenium)\n• Flask API 개발\n• 데이터 분석 및 시각화",
            "좋은 질문입니다! 💡 하지만 조금 더 구체적인 예시나 상황을 알려주시면 더 맞춤형 답변을 드릴 수 있어요.",
            "현재 해당 주제에 대한 자세한 답변을 준비 중입니다. 🔧 대신 다른 Python 관련 질문이 있으시면 언제든 물어보세요!"
        ]
    
    def process_message(self, message: str) -> Dict:
        """
        메시지를 처리하고 적절한 응답 반환
        
        Args:
            message: 사용자 입력 메시지
            
        Returns:
            응답 딕셔너리 (content, has_code, code_blocks)
        """
        message_lower = message.lower()
        
        # 패턴 매칭
        for pattern in self.qa_patterns:
            # 키워드 매칭
            if any(keyword in message_lower for keyword in pattern["keywords"]):
                # 정규식 패턴도 확인
                if re.search(pattern["question_pattern"], message_lower):
                    response = pattern["response"]
                    return {
                        "success": True,
                        "content": response["content"],
                        "has_code": len(response.get("code_blocks", [])) > 0,
                        "code_blocks": response.get("code_blocks", []),
                        "tokens_used": 0  # 모의 AI이므로 0
                    }
        
        # 매칭되는 패턴이 없으면 기본 응답
        default_response = random.choice(self.default_responses)
        return {
            "success": True,
            "content": default_response,
            "has_code": False,
            "code_blocks": [],
            "tokens_used": 0
        }

    def analyze_error(self, error_message: str, code: str = '', context: str = '') -> Dict[str, str]:
        """에러 분석 (간단한 패턴 매칭)"""
        common_errors = {
            "ModuleNotFoundError": {
                "explanation": "필요한 모듈이 설치되지 않았습니다.",
                "suggested_fix": "pip install [모듈명] 명령어로 모듈을 설치해주세요.",
                "fixed_code": "# pip install pandas numpy matplotlib\n" + code
            },
            "KeyError": {
                "explanation": "딕셔너리나 DataFrame에서 존재하지 않는 키에 접근했습니다.",
                "suggested_fix": "키 이름을 확인하거나 .get() 메소드를 사용해보세요.",
                "fixed_code": code.replace("[", ".get('").replace("]", "', None)")
            },
            "IndexError": {
                "explanation": "리스트나 배열의 범위를 벗어난 인덱스에 접근했습니다.",
                "suggested_fix": "인덱스 범위를 확인하거나 len() 함수로 크기를 먼저 체크해보세요.",
                "fixed_code": f"if len(data) > index:\n    {code}"
            }
        }
        
        for error_type, solution in common_errors.items():
            if error_type in error_message:
                return solution
        
        # 기본 응답
        return {
            "explanation": "일반적인 Python 에러가 발생했습니다. 코드를 다시 확인해보세요.",
            "suggested_fix": "변수명, 함수명, 들여쓰기를 확인해보세요.",
            "fixed_code": code
        }


# 전역 인스턴스
mock_ai = MockAI()

def get_ai_response(message: str) -> Dict:
    """AI 응답 가져오기 (전역 함수)"""
    return mock_ai.process_message(message)

def analyze_code_error(error_message: str, code: str = '', context: str = '') -> Dict[str, str]:
    """코드 에러 분석 (전역 함수)"""
    return mock_ai.analyze_error(error_message, code, context) 