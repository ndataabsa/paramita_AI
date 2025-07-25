"""
간단한 로깅 모듈
"""
import logging
import os
from datetime import datetime

# 에러 타입별 메시지 딕셔너리
ERROR_MESSAGES = {
    'login_failed': '로그인 실패',
    'session_expired': '세션 만료',
    'file_not_found': '파일을 찾을 수 없습니다',
    'permission_denied': '권한이 없습니다',
    'kernel_error': '커널 오류',
    'api_error': 'API 오류',
    'database_error': '데이터베이스 오류',
    'network_error': '네트워크 오류',
    'validation_error': '입력값 검증 오류',
    'system_error': '시스템 오류',
    'unknown_error': '알 수 없는 오류'
}

def log_message(error_type: str, error_message: str = None):
    """
    로그 출력 함수
    
    Args:
        error_type: 에러 타입 (ERROR_MESSAGES의 키 또는 사용자 정의 메시지)
        error_message: 에러 메시지 (None이면 ERROR_MESSAGES에서 가져옴)
    """
    # 로그 디렉토리 생성
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 로거 설정
    logger = logging.getLogger('NP_Notebook')
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정
    log_file = os.path.join(log_dir, f"np_notebook_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 로그 파일 권한 설정 (그룹 쓰기 권한 추가)
    try:
        os.chmod(log_file, 0o664)  # rw-rw-r--
    except Exception:
        pass  # 권한 설정 실패시 무시
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 메시지 결정
    if error_message is None:
        # error_type이 ERROR_MESSAGES의 키인 경우
        message = ERROR_MESSAGES.get(error_type, error_type)
    else:
        # error_type과 error_message를 조합
        message = f"{error_type}: {error_message}"
    
    # 로그 출력
    logger.error(message) 