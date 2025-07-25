# 프로젝트 설치 가이드

## 📋 필수 요구사항

### Python 버전
- Python 3.8 이상 권장

### 시스템 요구사항
- Linux/Windows/macOS 지원
- Chrome 브라우저 (Selenium용)
- 충분한 메모리 (최소 4GB 권장)

## 🚀 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd PROJECT_CRAWLER
```

### 2. 가상환경 생성 (권장)
```bash
# Python venv 사용
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. 라이브러리 설치
```bash
pip install -r requirements.txt
```

### 4. Chrome 드라이버 설치
```bash
# 자동 설치 (권장)
pip install webdriver-manager

# 또는 수동 설치
# https://chromedriver.chromium.org/ 에서 다운로드
```

## 🔧 설정

### 환경 변수 설정 (선택사항)
```bash
# .env 파일 생성
export FLASK_ENV=development
export FLASK_DEBUG=1
```

### 데이터베이스 설정
MySQL이나 Elasticsearch를 사용하는 경우 해당 설정을 `MODULE/connector.py`와 `MODULE/elasticconnector.py`에서 수정하세요.

## 🏃‍♂️ 실행 방법

### 기존 웹 애플리케이션 실행
```bash
python app.py
```
- 접속: http://localhost:53301/

### 주피터 스타일 웹 애플리케이션 실행
```bash
python jupyapp.py
```
- 접속: http://localhost:53301/

## 📁 프로젝트 구조
```
PROJECT_CRAWLER/
├── app.py                    # 기존 웹 애플리케이션
├── jupyapp.py               # 주피터 스타일 웹 애플리케이션
├── requirements.txt         # 필요한 라이브러리 목록
├── CLASS/                   # 핵심 클래스들
├── MODULE/                  # 모듈들
├── LIBS/PAGE/              # 페이지 관련 모듈들
├── templates/              # HTML 템플릿들
└── static/                 # 정적 파일들
```

## 🐛 문제 해결

### Chrome 드라이버 오류
```bash
# Chrome 버전 확인
google-chrome --version

# webdriver-manager로 자동 업데이트
pip install --upgrade webdriver-manager
```

### 포트 충돌
```bash
# 포트 사용 확인
netstat -tulpn | grep 53301

# 다른 포트 사용
python app.py --port 53302
```

### 권한 오류 (Linux)
```bash
# Chrome 실행 권한
chmod +x /usr/bin/google-chrome

# 가상 디스플레이 설정
export DISPLAY=:99
```

## 📚 주요 기능

### 웹 스크래핑
- Selenium 기반 브라우저 자동화
- BeautifulSoup4를 통한 HTML 파싱
- 다양한 데이터 추출 방법

### 웹 인터페이스
- Flask 기반 웹 애플리케이션
- 파일 브라우저
- Python 커널 실행
- 작업 관리 시스템

### 데이터 처리
- Pandas를 통한 데이터 분석
- MySQL/Elasticsearch 연동
- 다양한 형식으로 데이터 저장

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 