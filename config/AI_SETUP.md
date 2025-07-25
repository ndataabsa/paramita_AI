# 🤖 AI 코딩 어시스턴트 설정 가이드

## 📋 필요한 설정

### 1. API 키 설정

AI 어시스턴트 사용을 위해 환경변수를 설정해주세요:

```bash
# OpenAI API 키 (GPT 모델 사용 시)
export OPENAI_API_KEY="your_openai_api_key_here"

# Anthropic API 키 (Claude 모델 사용 시)
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
```

### 2. 라이브러리 설치

```bash
pip install openai>=1.0.0 anthropic>=0.8.0
```

### 3. 지원되는 AI 모델

- **OpenAI**: gpt-3.5-turbo, gpt-4, gpt-4-turbo
- **Anthropic**: claude-3-sonnet, claude-3-haiku

## 🚀 사용 방법

### 1. AI 채팅
- 우측 패널에서 🤖 채팅 탭 클릭
- 코딩 질문이나 요청 입력
- AI가 코드와 설명을 제공

### 2. 코드 실행
- AI가 생성한 코드 블록에서 ▶️ 버튼 클릭
- 실행 결과가 바로 표시됨
- 에러 발생 시 AI에게 수정 요청 가능

### 3. 코드 관리
- 📋 버튼: 코드 클립보드 복사
- 📓 버튼: 노트북에 코드 추가 (개발 중)

## ⚙️ 설정 변경

채팅 헤더의 ⚙️ 버튼을 클릭하여:
- AI 모델 선택
- 온도(창의성) 조절
- 시스템 프롬프트 수정

## 🔧 고급 설정

`config/ai_config.json` 파일에서 기본 설정 수정 가능:

```json
{
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 2000,
    "timeout": 30
}
```

## 📚 예시 질문

- "pandas로 CSV 파일을 읽고 기본 통계를 출력하는 코드를 작성해주세요"
- "selenium으로 웹페이지의 특정 요소를 클릭하는 방법"
- "이 에러를 수정해주세요: [에러 메시지]"
- "코드를 더 효율적으로 개선할 방법이 있나요?"

## 🛠️ 문제 해결

### API 키 오류
- 환경변수가 올바르게 설정되었는지 확인
- API 키가 유효한지 확인

### 코드 실행 실패
- 필요한 라이브러리가 설치되어 있는지 확인
- 커널이 정상적으로 실행 중인지 확인

### 응답 속도가 느림
- 더 빠른 모델(gpt-3.5-turbo) 사용
- max_tokens 값을 줄여서 응답 길이 단축 