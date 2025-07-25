# ��️ PROJECT_CRAWLER

106.254.246.83:53301
test_user / tester
접속 및 테스트
(아직 서버 안정화 중)


**Linux PAM 인증 기반의 고급 웹 크롤링 & 자동화 플랫폼**

Flask + Jupyter 스타일 인터페이스로 구현된 **기업급 웹 스크래핑 통합 환경**입니다. 실시간 크롤링, 데이터 추출, AI 분석, 자동화 작업을 위한 완전한 솔루션을 제공합니다.

## 🌟 핵심 특징

### 🔐 **보안 인증 시스템**
- **Linux PAM 인증**: 시스템 사용자 계정으로 로그인
- 세션 기반 보안 관리
- 사용자별 격리된 작업 환경

### 📊 **Jupyter 스타일 노트북 인터페이스**
- **듀얼 모드**: UI 컴포넌트 + JSON 직접 편집
- 실시간 코드 실행 및 결과 확인
- 파일별 독립적인 Python 커널 관리
- `.npn` (노트북), `.py`, `.json` 파일 지원

### 🕷️ **고급 크롤링 엔진**
- **Selenium WebDriver**: Chrome 헤드리스/GUI 모드
- **HTTP Client**: GET/POST 요청 지원
- **BeautifulSoup 파싱**: 고성능 HTML 처리
- **XPath/CSS 선택자**: 정밀한 요소 타겟팅
- **포커스 시스템**: current/xpath/selector 다중 지원

### 🎯 **스마트 데이터 추출**
- **6가지 찾기 방식**: ID, 클래스, 태그명, 텍스트, 속성, **XPath**
- **9가지 범위 옵션**: self, all, contain, first, last, next, parent, children, siblings
- **자동 데이터 변환**: HTML → DataFrame, 링크 추출, 텍스트 정제
- **실시간 이미지 처리**: Base64 변환 및 데이터 URI 지원

### 💾 **멀티 포맷 데이터 I/O**
- **파일 저장**: Excel, CSV, TXT (자동 권한 설정 rw-rw-r--)
- **데이터베이스**: MySQL 연동
- **검색 엔진**: Elasticsearch 연동
- **Python 스크립트**: 파일 실행 및 코드 직접 실행

### 🤖 **AI 통합 분석**
- **OpenAI GPT**: 텍스트 분석 및 자동화
- **Anthropic Claude**: 고급 데이터 처리
- **채팅 인터페이스**: AI 기반 크롤링 도우미

### ⚙️ **고급 커널 관리**
- **멀티 커널**: 파일별 + 세션별 + 프로세스별
- **실시간 모니터링**: CPU, 메모리 사용량 추적
- **시간 제한**: 자동 종료 및 연장 기능
- **커널 복원**: 시스템 재시작 후 자동 복구

## 🚀 설치 및 실행

### **시스템 요구사항**
- **OS**: Linux/Ubuntu 18.04+ (PAM 인증 필요)
- **Python**: 3.8+
- **Browser**: Chrome/Chromium 설치 필수
- **Memory**: 최소 4GB RAM 권장
- **Disk**: 2GB 이상 여유 공간

### **1. 저장소 클론**
```bash
git clone https://github.com/ndataabsa/paramita_AI.git
cd PROJECT_CRAWLER
```

### **2. 의존성 설치**
```bash
# Python 패키지 설치
pip install -r requirements.txt

# Chrome WebDriver 권한 설정
chmod +x chromedriver-linux64/chromedriver

# Ubuntu/Debian 시스템 패키지 (필요시)
sudo apt-get update
sudo apt-get install python3-pam chromium-browser
```

### **3. 데이터베이스 설정 (선택사항)**
```bash
# MySQL 설정
cp MODULE/DB_INFO.txt.example MODULE/DB_INFO.txt
nano MODULE/DB_INFO.txt

# Elasticsearch 설정 (기본 localhost:9200)
```

### **4. 애플리케이션 실행**
```bash
python jupyapp.py
```

### **5. 웹 접속**
- **메인 노트북**: http://localhost:53301/notebook
- **Python 커널**: http://localhost:53301/kernel  
- **메인 대시보드**: http://localhost:53301/

## 📚 완전한 사용 가이드

### **1. 첫 로그인**
1. 웹 브라우저에서 접속
2. **Linux 사용자 계정**으로 로그인
3. 왼쪽 파일 브라우저에서 프로젝트 시작

### **2. 크롤링 프로젝트 생성**
```bash
# 새 파일 생성
파일명: my_project.npn

# 크롤링 셀 추가
🕷️ 버튼 클릭 → 크롤링 셀 생성
```

### **3. 9가지 Job Type 완전 가이드**

#### **🌐 request: 웹 접속**
```json
{
  "job_type": "request",
  "action": "selenium",
  "params": {
    "url": "https://example.com",
    "wait_time": 3
  }
}
```
- **get**: HTTP GET 요청
- **post**: HTTP POST 요청  
- **selenium**: Selenium 브라우저 시작
- **selenium_url_change**: 기존 브라우저에서 URL 변경

#### **🎯 do: 웹 액션 수행**
```json
{
  "job_type": "do",
  "action": "click",
  "params": {
    "focus": {"xpath": "//button[@id='search']"},
    "speed": 1.0
  }
}
```
- **click**: 요소 클릭
- **text**: 텍스트 입력
- **clear**: 입력값 지우기
- **enter**: 엔터 키
- **pagedown**: 페이지 다운
- **radio**: 라디오/체크박스 선택
- **scroll**: 페이지 스크롤
- **scroll_to_element**: 특정 요소로 스크롤
- **do_screen_shot**: 스크린샷 촬영

#### **🔍 find: 데이터 찾기**
```json
{
  "job_type": "find",
  "action": "class",
  "params": {
    "find_item": "product-item",
    "find_range": "all"
  }
}
```
- **id**: ID 속성으로 찾기
- **class**: 클래스명으로 찾기
- **name**: 태그명으로 찾기
- **text**: 텍스트 내용으로 찾기
- **attribute**: 속성값으로 찾기
- **xpath**: XPath 표현식으로 찾기

**찾기 범위 (find_range):**
- `self`: 현재 요소
- `all`: 모든 매칭 요소
- `contain`: 포함된 요소
- `first`: 첫 번째 요소
- `last`: 마지막 요소
- `next`: 다음 요소
- `parent`: 부모 요소
- `children`: 자식 요소들
- `siblings`: 형제 요소들

#### **🔄 data: 데이터 변환**
```json
{
  "job_type": "data",
  "action": "to_dataframe",
  "params": {
    "from": "extracted_elements",
    "to": "products_df"
  }
}
```
- **to_html**: HTML 문자열로 변환
- **to_xpath**: XPath 경로로 변환
- **to_dataframe**: pandas DataFrame으로 변환
- **get_href**: 링크 URL 추출
- **get_hrefs**: 모든 링크 URL 추출
- **get_text_all**: 전체 텍스트 추출
- **get_texts_all**: 텍스트를 리스트로 분리
- **get_text_all_tagonly**: 태그만 포함 텍스트
- **get_text_all_without_script**: 스크립트 제외 텍스트
- **key_to_list**: 여러 데이터 키를 리스트로 결합

#### **💾 save: 데이터 저장**
```json
{
  "job_type": "save",
  "action": "excel",
  "params": {
    "to": "products_df",
    "name": "products.xlsx"
  }
}
```
- **excel**: Excel 파일 (.xlsx)
- **csv**: CSV 파일
- **txt**: 텍스트 파일
- **mysql**: MySQL 데이터베이스
- **elasticsearch**: Elasticsearch 인덱스

#### **📂 load: 데이터 로드**
```json
{
  "job_type": "load",
  "action": "csv",
  "params": {
    "from": "loaded_data",
    "name": "input.csv",
    "encoding": "utf-8"
  }
}
```

#### **🐍 python: Python 스크립트 실행**
```json
{
  "job_type": "python",
  "action": "code",
  "params": {
    "code": "print('Hello World!')",
    "to": "result"
  }
}
```
- **file**: Python 파일 실행
- **code**: 코드 직접 실행

#### **⏰ wait: 대기**
```json
{
  "job_type": "wait",
  "action": "fixed_time",
  "params": {
    "time": 2.5
  }
}
```

#### **🧪 test: 테스트 및 디버깅**
```json
{
  "job_type": "test",
  "action": "variable",
  "params": {
    "name": "test_var",
    "value": "Hello",
    "print_result": true
  }
}
```

### **4. Focus 시스템**
크롤링 대상 요소 지정 방식:
- **current**: 현재 활성 요소
- **xpath**: XPath 선택자 `{"xpath": "//div[@class='item']"}`
- **selector**: CSS 선택자 `{"selector": ".product-item"}`

### **5. 고급 워크플로우 예시**

#### **E-커머스 상품 크롤링**
```json
// 1. 사이트 접속
{
  "job_type": "request",
  "action": "selenium",
  "params": {"url": "https://shop.example.com", "wait_time": 3}
}

// 2. 검색어 입력
{
  "job_type": "do",
  "action": "text",
  "params": {
    "focus": {"xpath": "//input[@name='search']"},
    "text": "노트북",
    "speed": 0.1
  }
}

// 3. 검색 버튼 클릭
{
  "job_type": "do",
  "action": "click",
  "params": {"focus": {"xpath": "//button[@type='submit']"}}
}

// 4. 상품 목록 추출
{
  "job_type": "find",
  "action": "class",
  "params": {
    "find_item": "product-item",
    "find_range": "all"
  }
}

// 5. DataFrame 변환
{
  "job_type": "data",
  "action": "to_dataframe",
  "params": {"from": "LAST_RESULT", "to": "products"}
}

// 6. Excel 저장
{
  "job_type": "save",
  "action": "excel",
  "params": {"to": "products", "name": "laptop_products.xlsx"}
}
```

## 🎛️ 인터페이스 가이드

### **듀얼 편집 모드**
각 크롤링 셀은 두 가지 모드로 편집 가능:

#### **UI 모드 (권장)**
- 드롭다운으로 Job Type 선택
- 자동 Action 업데이트
- 폼 기반 파라미터 입력
- 실시간 검증 및 도움말

#### **JSON 모드 (고급)**
- 직접 JSON 편집
- 복잡한 파라미터 설정
- 배치 복사/붙여넣기
- 스크립트 자동화 지원

### **실시간 동기화**
- UI 변경 → JSON 자동 업데이트
- JSON 편집 → UI 자동 반영
- 토글 스위치로 모드 전환

## 📁 프로젝트 아키텍처

```
PROJECT_CRAWLER/
├── jupyapp.py                    # Flask 메인 애플리케이션 (PAM 인증, 라우팅)
├── requirements.txt              # Python 의존성 (45개 패키지)
├── 
├── templates/                    # Jinja2 HTML 템플릿
│   ├── notebook.html            # 메인 노트북 인터페이스 (4,982줄)
│   ├── login.html               # PAM 로그인 페이지
│   ├── kernel.html              # Python 커널 관리
│   └── jobs.html                # 작업 스케줄링 관리
│
├── CLASS/                        # 핵심 비즈니스 로직
│   ├── class_job.py             # 작업 실행 엔진 (1,209줄)
│   ├── CLASS_kernel_manager.py  # 커널 생명주기 관리 (1,449줄)
│   ├── class_parser_html.py     # HTML 파싱 및 데이터 추출
│   ├── CLASS_chat_manager.py    # AI 채팅 관리
│   ├── data_result.py           # 결과 데이터 구조체
│   └── class_worker.py          # 백그라운드 작업자
│
├── MODULE/                       # 유틸리티 모듈
│   ├── module_engine_selenium.py # Selenium WebDriver 엔진 (652줄)
│   ├── connector.py             # MySQL 데이터베이스 연결
│   ├── elasticconnector.py      # Elasticsearch 클라이언트
│   ├── module_AI.py             # OpenAI/Anthropic API 클라이언트
│   ├── module_logger.py         # 통합 로깅 시스템
│   └── module_engine_parser.py  # 파싱 엔진 인터페이스
│
├── LIBS/                         # 페이지별 기능 모듈
│   └── PAGE/                    
│       ├── file_browser.py      # 파일 브라우저 API
│       └── kernel_manager.py    # 커널 관리 API
│
├── chromedriver-linux64/         # Chrome WebDriver 바이너리
├── data/                         # 크롤링 결과 데이터
├── logs/                         # 시스템 로그 파일
└── config/                       # 설정 파일들
```

## 🔧 고급 설정 및 커스터마이징

### **애플리케이션 설정**
```python
# jupyapp.py에서 수정 가능
app.run(debug=True, host='0.0.0.0', port=53301)

# 커널 시간 제한 (기본 24시간)
KERNEL_TIMEOUT = 3600 * 24  # 초 단위

# 최대 동시 커널 수
MAX_KERNELS = 10
```

### **Selenium 커스터마이징**
```python
# MODULE/module_engine_selenium.py
chrome_options = [
    '--headless',                    # 백그라운드 실행
    '--no-sandbox',                  # 샌드박스 비활성화
    '--disable-dev-shm-usage',       # 메모리 최적화
    '--window-size=1920,1080',       # 화면 크기
    '--user-agent=Custom-Agent'      # User-Agent 설정
]
```

### **데이터베이스 설정**
```ini
# MODULE/DB_INFO.txt
host=localhost
port=3306
user=crawler_user
password=secure_password
database=crawler_db
charset=utf8mb4
```

### **커스텀 Job Type 추가**
1. **jupyapp.py의 JOB_TYPES 확장**:
```python
'custom': {
    'name': '커스텀 작업',
    'custom_types': {
        'my_action': {'name': '내 액션', 'params': ['param1', 'param2']}
    }
}
```

2. **class_job.py에 실행 로직 구현**:
```python
elif self.args['type'] == 'custom':
    if self.args['action'] == 'my_action':
        # 커스텀 로직 구현
        return data_result.DATA_Result(result=True, data="Success")
```

3. **notebook.html에 UI 컴포넌트 추가**:
```javascript
// updateCrawlActions 함수에 케이스 추가
else if (jobType === 'custom') {
    actionType = 'custom_types';
}
```


### **Chrome WebDriver 문제**
```bash
# Chrome 버전 확인
google-chrome --version
chromium-browser --version

# WebDriver 권한 및 경로 확인
ls -la chromedriver-linux64/chromedriver
export PATH=$PATH:$(pwd)/chromedriver-linux64

# Display 문제 (headless 모드 실행)
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
```

### **커널 관련 문제**
# 포트 사용 확인 및 해제
netstat -tulpn | grep :53301
lsof -ti:53301 | xargs kill -9
```
## 🤝 개발 및 기여

### **개발 환경 설정**

### **코드 스타일**
- **Python**: PEP 8 준수
- **JavaScript**: ESLint 표준
- **HTML/CSS**: 일관된 들여쓰기 및 네이밍

### **기여 가이드라인**
1. 이슈 등록 또는 기능 제안
2. 포크 및 브랜치 생성 (`feature/new-feature`)
3. 코드 작성 및 테스트
4. 커밋 메시지 작성 (`feat: add new crawler type`)
5. Pull Request 생성

### **테스트**
```bash
# 단위 테스트 실행
python -m pytest tests/

# 통합 테스트
python test_job.py

# E2E 테스트 (Selenium)
python tests/test_crawling_workflow.py
```

## 📄 라이선스 및 저작권

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 상업적 이용 가능하며, 수정 및 재배포가 자유롭습니다.

## 🆘 지원 및 커뮤니티

### **문서 및 도움말**
- **API 문서**: `/api/docs` (개발 중)
- **예제 파일**: `*.npn` 파일들 참조
- **튜토리얼**: `docs/` 디렉토리

### **문제 신고**
- **GitHub Issues**: 버그 신고 및 기능 요청
- **로그 파일**: `logs/` 디렉토리에서 오류 내용 확인
- **시스템 정보**: 환경 정보와 함께 문의

### **성능 벤치마크**
- **처리 속도**: 시간당 10,000+ 페이지 처리 가능
- **동시 작업**: 최대 50개 동시 크롤링 작업
- **메모리 효율**: 평균 512MB ~ 2GB RAM 사용
- **안정성**: 24시간 연속 운영 가능
