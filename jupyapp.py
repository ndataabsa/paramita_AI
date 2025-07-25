"""
주피터 스타일 웹 애플리케이션
파일 브라우저와 Python 커널을 포함한 통합 환경
"""
from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
import json
import glob
import os
import atexit
import pam  # pip install python-pam 필요
from functools import wraps
from MODULE.module_logger import log_message

# 모듈화된 함수들 import
from LIBS.PAGE.file_browser import (
    get_files, get_file_content, save_file, download_file, 
    delete_file, create_file, upload_file, rename_file, get_file_browser_page_data
)
from LIBS.PAGE.kernel_manager import *

app = Flask(__name__)
app.secret_key = 'jupyter-style-secret-key'

# 로그인 필요 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 로그인 라우트
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if pam.pam().authenticate(user_id, password):
            session['user_id'] = user_id
            log_message('login_success', f'사용자 {user_id} 로그인 성공')
            return redirect(url_for('notebook_page'))
        else:
            log_message('login_failed', f'사용자 {user_id} 로그인 실패')
            return render_template('login.html', error='로그인 실패')
    return render_template('login.html')

# 로그아웃 라우트
@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_message('logout', f'사용자 {user_id} 로그아웃')
    session.pop('user_id', None)
    return redirect(url_for('login'))

# class_job.py에서 추출한 명령어 타입들
JOB_TYPES = {
    'do': {
        'name': '액션 수행',
        'actions': {
            'click': {'name': '클릭', 'params': ['focus', 'speed']},
            'text': {'name': '텍스트 입력', 'params': ['focus', 'text', 'speed']},
            'clear': {'name': '텍스트 지우기', 'params': ['focus', 'speed']},
            'enter': {'name': '엔터', 'params': []},
            'pagedown': {'name': '페이지 다운', 'params': []},
            'radio': {'name': '라디오/체크박스', 'params': ['focus', 'value']},
            'scroll': {'name': '스크롤', 'params': ['sleep', 'max_time', 'speed_variation']},
            'scroll_to_element': {'name': '요소로 스크롤', 'params': ['focus', 'sleep', 'speed', 'speed_variation', 'max_time']},
            'do_screen_shot': {'name': '스크린샷 촬영', 'params': ['filename']}
        }
    },
    'find': {
        'name': '데이터 찾기',
        'find_types': {
            'id': {'name': 'ID로 찾기', 'params': ['find_item', 'find_range']},
            'class': {'name': '클래스로 찾기', 'params': ['find_item', 'find_range']},
            'name': {'name': '태그명으로 찾기', 'params': ['find_item', 'find_range']},
            'text': {'name': '텍스트로 찾기', 'params': ['find_item', 'find_range']},
            'attribute': {'name': '속성으로 찾기', 'params': ['find_attribute', 'find_item', 'find_range']},
            'xpath': {'name': 'xpath로 찾기', 'params': ['find_item']}
        },
        'find_ranges': ['self', 'all', 'contain', 'first', 'last', 'next', 'parent', 'children', 'siblings']
    },
    'request': {
        'name': '인터넷 연결',
        'request_types': {
            'get': {'name': 'GET 요청', 'params': ['url', 'params']},
            'post': {'name': 'POST 요청', 'params': ['url', 'data']},
            'selenium': {'name': 'Selenium 요청', 'params': ['url', 'wait_time']},
            'selenium_url_change': {'name': 'Selenium URL 변경', 'params': ['url', 'wait_time']}
        },
        'params': ['request_type', 'url', 'data', 'wait_time']
    },
    'data': {
        'name': '데이터 변환',
        'convert_types': {
            'to_html': {'name': 'HTML로 변환', 'params': ['from', 'to']},
            'to_xpath': {'name': 'XPath로 변환', 'params': ['from', 'to']},
            'to_dataframe': {'name': 'DataFrame으로 변환', 'params': ['from', 'to']},
            'get_href': {'name': 'HREF 추출', 'params': ['from', 'to', 'href_arg']},
            'get_hrefs': {'name': 'HREF들 추출', 'params': ['from', 'to', 'href_arg']},
            'get_text_all': {'name': '모든 텍스트 추출', 'params': ['from', 'to', 'text_arg']},
            'get_texts_all': {'name': '텍스트를 리스트로 분리 추출', 'params': ['from', 'to', 'text_arg']},
            'get_text_all_tagonly': {'name': '태그만 텍스트 추출', 'params': ['from', 'to', 'text_arg']},
            'get_text_all_without_script': {'name': '스크립트 제외 텍스트 추출', 'params': ['from', 'to', 'text_arg']},
            'key_to_list': {'name': '키들을 리스트로 변환', 'params': ['to', 'key_count']}
        },
        'params': ['from', 'to', 'convert_type']
    },
    'save': {
        'name': '데이터 저장',
        'save_types': {
            'excel': {'name': 'Excel 저장', 'params': ['save_type', 'to', 'name']},
            'csv': {'name': 'CSV 저장', 'params': ['save_type', 'to', 'name', 'encoding']},
            'txt': {'name': 'TXT 저장', 'params': ['save_type', 'to', 'name', 'encoding']},
            'mysql': {'name': 'MySQL 저장', 'params': ['to', 'name']},
            'elasticsearch': {'name': 'Elasticsearch 저장', 'params': ['to', 'name']}
        },
        'params': ['save_type', 'to', 'name', 'encoding']
    },
    'load': {
        'name': '데이터 로드',
        'load_types': {
            'excel': {'name': 'Excel 로드', 'params': ['load_type', 'from', 'name']},
            'csv': {'name': 'CSV 로드', 'params': ['load_type', 'from', 'name', 'encoding']},
            'txt': {'name': 'TXT 로드', 'params': ['load_type', 'from', 'name', 'encoding']},
            'mysql': {'name': 'MySQL 로드', 'params': ['from', 'name']},
            'elasticsearch': {'name': 'Elasticsearch 로드', 'params': ['from', 'name']}
        },
        'params': ['load_type', 'from', 'name', 'encoding']
    },
    'python': {
        'name': 'Python 스크립트 실행',
        'python_types': {
            'file': {'name': '파일 실행', 'params': ['script_path', 'to', 'arg_count']},
            'code': {'name': '코드 직접 실행', 'params': ['code', 'to']}
        },
        'params': ['python_type', 'script_path', 'to', 'arg_count', 'code']
    },
    'wait': {
        'name': '대기',
        'wait_types': {
            'fixed_time': {'name': '고정 시간 대기', 'params': ['time']},
            'load_time': {'name': '로딩 완료 대기', 'params': []}
        },
        'params': ['wait_type', 'time']
    },
    'test': {
        'name': '테스트',
        'test_types': {
            'variable': {'name': '변수 저장 및 출력', 'params': ['name', 'value', 'print_result']},
            'list': {'name': '리스트 생성 및 출력', 'params': ['name', 'items', 'print_result']},
            'dict': {'name': '딕셔너리 생성 및 출력', 'params': ['name', 'key_value_pairs', 'print_result']}
        },
        'params': ['test_type', 'name', 'value', 'print_result']
    }
}

FOCUS_TYPES = ['xpath', 'selector', 'current']

# 앱 종료 시 모든 커널 정리
def shutdown_all_kernels():
    """앱 종료 시 모든 커널을 정리합니다."""
    try:
        from CLASS import CLASS_kernel_manager
        CLASS_kernel_manager.kernel_manager.shutdown_all()
    except Exception as e:
        log_message('system_error', f'커널 정리 중 오류: {str(e)}')

atexit.register(shutdown_all_kernels)

# 복잡한 JavaScript 코드들과 처리 로직은 CLASS_kernel_manager.py의 Kernel 클래스로 이동됨





# 메인 페이지
@app.route('/')
@login_required
def index():
    """메인 페이지 - 주피터 스타일 대시보드"""
    # 현재 디렉토리의 JSON 파일들 찾기
    json_files = glob.glob('*.json')
    
    # 선택된 파일 (기본값: 없음)
    selected_file = request.args.get('file', '')
    
    # 선택된 파일이 존재하지 않으면 첫 번째 파일 사용
    if selected_file and selected_file not in json_files and json_files:
        selected_file = json_files[0]
    elif not selected_file and json_files:
        selected_file = json_files[0]
    
    return render_template('jupyter_index.html', json_files=json_files, selected_file=selected_file, user_id=session['user_id'])

# Paramita AI 페이지
@app.route('/notebook')
@login_required
def notebook_page():
    user_id = session.get('user_id')
    data = get_file_browser_page_data(user_id=user_id)
    # JOB_TYPES와 FOCUS_TYPES를 템플릿에 직접 전달
    data['job_types'] = JOB_TYPES
    data['focus_types'] = FOCUS_TYPES
    return render_template('notebook.html', **data)

# Python 커널 페이지
@app.route('/kernel')
@login_required
def kernel_page():
    """Python 커널 페이지를 반환합니다."""
    return render_template('kernel.html', user_id=session['user_id'])



# 파일 브라우저 API 엔드포인트들
@app.route('/api/files', methods=['GET'])
@login_required
def api_get_files():
    return get_files()

@app.route('/api/files/content', methods=['GET'])
@login_required
def api_get_file_content():
    return get_file_content()

@app.route('/api/files/save', methods=['POST'])
@login_required
def api_save_file():
    return save_file()

@app.route('/api/files/download', methods=['GET'])
@login_required
def api_download_file():
    return download_file()

@app.route('/api/files/delete', methods=['POST'])
@login_required
def api_delete_file():
    return delete_file()

@app.route('/api/files/create', methods=['POST'])
@login_required
def api_create_file():
    return create_file()

@app.route('/api/files/upload', methods=['POST'])
@login_required
def api_upload_file():
    return upload_file()

@app.route('/api/files/rename', methods=['POST'])
@login_required
def api_rename_file():
    return rename_file()

@app.route('/api/files/image', methods=['GET'])
@login_required
def api_get_image():
    """이미지 파일을 직접 서빙합니다."""
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'success': False, 'message': '파일 경로가 필요합니다.'}), 400
        
        # 보안 검사: 상대 경로만 허용
        if file_path.startswith('/') or '..' in file_path:
            return jsonify({'success': False, 'message': '잘못된 파일 경로입니다.'}), 400
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404
        
        # 이미지 파일 확장자 확인
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension not in image_extensions:
            return jsonify({'success': False, 'message': '이미지 파일이 아닙니다.'}), 400
        
        # 이미지 파일을 직접 반환
        return send_file(file_path, mimetype='image/' + file_extension[1:])
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'이미지 로드 중 오류: {str(e)}'}), 500

# 커널 API 엔드포인트들
@app.route('/api/kernels', methods=['GET'])
@login_required
def api_get_kernels():
    return get_kernels()

@app.route('/api/kernels', methods=['POST'])
@login_required
def api_create_new_kernel():
    return create_new_kernel()

@app.route('/api/kernels/file-user', methods=['POST'])
@login_required
def api_create_file_user_kernel():
    return create_file_user_kernel()

@app.route('/api/kernels/<kernel_id>', methods=['DELETE'])
@login_required
def api_delete_kernel(kernel_id):
    return delete_kernel_api(kernel_id)

@app.route('/api/kernels/<kernel_id>/status', methods=['GET'])
@login_required
def api_get_kernel_status(kernel_id):
    return get_kernel_status_api(kernel_id)

@app.route('/api/kernels/<kernel_id>/execute', methods=['POST'])
@login_required
def api_execute_kernel_code(kernel_id):
    return execute_kernel_code(kernel_id)

@app.route('/api/kernels/<kernel_id>/history', methods=['GET'])
@login_required
def api_get_kernel_history(kernel_id):
    return get_kernel_history(kernel_id)

@app.route('/api/kernels/<kernel_id>/namespace', methods=['GET'])
@login_required
def api_get_kernel_namespace(kernel_id):
    return get_kernel_namespace(kernel_id)

@app.route('/api/kernels/<kernel_id>/shared-dict', methods=['GET'])
@login_required
def api_get_shared_dict(kernel_id):
    return get_shared_dict(kernel_id)

@app.route('/api/kernels/<kernel_id>/clear', methods=['POST'])
@login_required
def api_clear_kernel_namespace(kernel_id):
    return clear_kernel_namespace(kernel_id)

# 프로세스 커널 관련 API 엔드포인트들
@app.route('/api/kernels/scan-process', methods=['POST'])
@login_required
def api_scan_process_kernels():
    return scan_process_kernels_api()

@app.route('/api/kernels/<kernel_id>/process-status', methods=['GET'])
@login_required
def api_get_process_kernel_status(kernel_id):
    return get_process_kernel_status_api(kernel_id)

@app.route('/api/kernels/<kernel_id>/terminate-process', methods=['POST'])
@login_required
def api_terminate_process_kernel(kernel_id):
    return terminate_process_kernel_api(kernel_id)

@app.route('/api/kernels/add-process-to-project', methods=['POST'])
@login_required
def api_add_process_kernel_to_project():
    return add_process_kernel_to_project_api()

@app.route('/api/kernels/<kernel_id>/project-status', methods=['GET'])
@login_required
def api_check_kernel_project_status(kernel_id):
    return check_kernel_project_status_api(kernel_id)

# 세션별 커널 API 엔드포인트들
@app.route('/api/session/kernel/status', methods=['GET'])
@login_required
def api_get_session_kernel_status():
    return get_session_kernel_status()

@app.route('/api/session/kernel/execute', methods=['POST'])
@login_required
def api_execute_session_kernel_code():
    return execute_session_kernel_code()

@app.route('/api/session/kernel/namespace', methods=['GET'])
@login_required
def api_get_session_kernel_namespace():
    return get_session_kernel_namespace()

@app.route('/api/session/kernel/clear', methods=['POST'])
@login_required
def api_clear_session_kernel_namespace():
    return clear_session_kernel_namespace()

@app.route('/api/session/kernel/history', methods=['GET'])
@login_required
def api_get_session_kernel_history():
    return get_session_kernel_history()

@app.route('/api/session/kernel/cleanup', methods=['POST'])
@login_required
def api_cleanup_session_kernel():
    return cleanup_session_kernel_api()

# 파일-커널 매핑 API 엔드포인트들
@app.route('/api/kernels/file-mapping', methods=['POST'])
@login_required
def api_set_file_kernel_mapping():
    return set_file_kernel_mapping_api()

@app.route('/api/kernels/file-mapping', methods=['GET'])
@login_required
def api_get_file_kernel_mapping():
    return get_file_kernel_mapping_api()

@app.route('/api/kernels/file-mapping', methods=['DELETE'])
@login_required
def api_remove_file_kernel_mapping():
    return remove_file_kernel_mapping_api()

@app.route('/api/kernels/file-mappings', methods=['GET'])
@login_required
def api_get_all_file_kernel_mappings():
    return get_all_file_kernel_mappings_api()

# 커널 시간제한 관련 API 엔드포인트들
@app.route('/api/kernels/<kernel_id>/remaining-time', methods=['GET'])
@login_required
def api_get_kernel_remaining_time(kernel_id):
    """커널의 남은 시간을 반환합니다."""
    return get_kernel_remaining_time(kernel_id)

@app.route('/api/kernels/<kernel_id>/extend-timeout', methods=['POST'])
@login_required
def api_extend_kernel_timeout(kernel_id):
    """커널 시간제한을 연장합니다."""
    try:
        data = request.get_json()
        additional_hours = data.get('additional_hours', 12) if data else 12
        return extend_kernel_timeout(kernel_id, additional_hours)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/session/kernel/remaining-time', methods=['GET'])
@login_required
def api_get_session_kernel_remaining_time():
    """세션 커널의 남은 시간을 반환합니다."""
    try:
        from LIBS.PAGE.kernel_manager import get_session_kernel_id
        kernel_id = get_session_kernel_id()
        return get_kernel_remaining_time(kernel_id)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/session/kernel/extend-timeout', methods=['POST'])
@login_required
def api_extend_session_kernel_timeout():
    """세션 커널 시간제한을 연장합니다."""
    try:
        from LIBS.PAGE.kernel_manager import get_session_kernel_id
        data = request.get_json()
        additional_hours = data.get('additional_hours', 12) if data else 12
        kernel_id = get_session_kernel_id()
        return extend_kernel_timeout(kernel_id, additional_hours)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Job 실행 API 엔드포인트
@app.route('/run_job', methods=['POST'])
@login_required
def run_job():
    """개별 job을 실행합니다."""
    try:
        data = request.get_json()
        job = data.get('job', {})
        selected_file = data.get('selected_file', 'contraction.json')
        
        if not job:
            return jsonify({'success': False, 'message': '실행할 job이 없습니다'})
        
        # 세션 커널에서 공유 데이터 가져오기
        from LIBS.PAGE.kernel_manager import get_session_kernel
        kernel = get_session_kernel()
        if kernel is None:
            return jsonify({'success': False, 'message': '세션 커널을 초기화할 수 없습니다'})
        
        data_share_dict = kernel.get_namespace()
        
        # engine 초기화 (커널에서 사용할 수 있도록)
        if 'worker_class_engine' not in data_share_dict:
            from MODULE.module_engine_selenium import engine
            data_share_dict['worker_class_engine'] = engine()
            data_share_dict['driver_number'] = 0
            kernel.namespace.update(data_share_dict)
        
        # Job 클래스를 직접 사용하여 실행
        from CLASS.class_job import Job
        job_instance = Job(job.get('name', ''), job.get('params', {}), data_share_dict)
        result = job_instance.run()
        
        # 실행 결과를 세션 커널의 네임스페이스에 저장
        updated_namespace = kernel.get_namespace()
        
        # JSON 직렬화 가능한 데이터만 필터링
        import json
        serializable_data = {}
        for key, value in updated_namespace.items():
            try:
                # JSON 직렬화 테스트
                json.dumps(value)
                serializable_data[key] = value
            except (TypeError, ValueError):
                # 직렬화 불가능한 객체는 문자열로 변환
                serializable_data[key] = f"<{type(value).__name__} object>"
        
        if result['result']:
            return jsonify({
                'success': True, 
                'message': result['message'],
                'data': serializable_data
            })
        else:
            return jsonify({
                'success': False, 
                'message': result['message'],
                'data': serializable_data
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Job 실행 중 오류 발생: {str(e)}'})

# Job Types API 엔드포인트
@app.route('/api/job_types', methods=['GET'])
@login_required
def api_get_job_types():
    """JOB_TYPES와 FOCUS_TYPES를 반환합니다."""
    return jsonify({
        'job_types': JOB_TYPES,
        'focus_types': FOCUS_TYPES
    })

# 컴포넌트 파일 제공 라우트
@app.route('/templates/component/<path:filename>')
@login_required
def serve_component(filename):
    """컴포넌트 파일을 제공합니다."""
    try:
        component_path = os.path.join('templates', 'component', filename)
        if os.path.exists(component_path):
            return send_file(component_path)
        else:
            return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'파일 로드 중 오류: {str(e)}'}), 500

# CSS 파일 제공 라우트
@app.route('/templates/<path:filename>')
@login_required
def serve_template_file(filename):
    """templates 폴더의 파일을 제공합니다."""
    try:
        file_path = os.path.join('templates', filename)
        if os.path.exists(file_path):
            # CSS 파일인 경우 적절한 MIME 타입 설정
            if filename.endswith('.css'):
                return send_file(file_path, mimetype='text/css')
            return send_file(file_path)
        else:
            return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'파일 로드 중 오류: {str(e)}'}), 500

@app.route('/api/html-viewer/refresh-selenium', methods=['POST'])
@login_required
def api_refresh_selenium_data():
    """HTML 뷰어용: SYSTEM_SELENIUM 데이터 새로고침"""
    try:
        data = request.get_json()
        kernel_id = data.get('kernel_id') if data else None
        scroll_x = data.get('scroll_x', 0) if data else 0
        scroll_y = data.get('scroll_y', 0) if data else 0
        
        if not kernel_id:
            return jsonify({'success': False, 'error': '커널 ID가 필요합니다'})
        
        # kernel_manager의 새로고침 함수 호출 (복잡한 로직이 이동됨)
        from LIBS.PAGE.kernel_manager import refresh_selenium_data_with_conversion
        
        result = refresh_selenium_data_with_conversion(kernel_id, scroll_x, scroll_y)
        
        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'API 오류: {str(e)}'})


@app.route('/api/html-viewer/reset-init', methods=['POST'])
@login_required
def api_reset_html_conversion_init():
    """HTML 뷰어용: HTML 변환 초기화 변수를 False로 리셋"""
    try:
        data = request.get_json()
        kernel_id = data.get('kernel_id') if data else None
        
        if not kernel_id:
            return jsonify({'success': False, 'error': '커널 ID가 필요합니다'})
        
        # kernel_manager의 init 리셋 함수 호출
        from LIBS.PAGE.kernel_manager import reset_html_conversion_init
        
        result = reset_html_conversion_init(kernel_id)
        
        if result['success']:
            return jsonify({
                'success': True, 
                'message': result['message'],
                'details': {
                    'old_value': result['old_value'],
                    'new_value': result['new_value'],
                    'cache_cleared': result['cache_cleared']
                }
            })
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'API 오류: {str(e)}'})

# AI 코딩 어시스턴트 API 엔드포인트들
@app.route('/api/ai/chat', methods=['POST'])
@login_required
def api_ai_chat():
    """AI와 채팅하고 코드 생성 요청 (Mock AI 사용)"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        chat_id = data.get('chat_id')  # 채팅 ID
        
        if not message.strip():
            return jsonify({'success': False, 'error': '메시지가 비어있습니다'})
        
        # 채팅 매니저에서 처리
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        
        # 채팅 ID가 없으면 새 채팅 생성
        if not chat_id:
            chat = chat_manager.create_chat(user_id, "새 채팅")
            chat_id = chat.id
        
        # 메시지 처리
        response = chat_manager.process_user_message(chat_id, message)
        
        if response['success']:
            return jsonify({
                'success': True,
                'response': response['response'],
                'has_code': response.get('has_code', False),
                'code_blocks': response.get('code_blocks', []),
                'chat_id': chat_id,
                'chat_title': response.get('chat_title', '새 채팅'),
                'tokens_used': 0  # Mock AI는 토큰 사용량 없음
            })
        else:
            return jsonify({'success': False, 'error': response.get('error', 'AI 응답 실패')})
        
    except Exception as e:
        log_message(f"AI 채팅 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'AI 채팅 중 오류: {str(e)}'})

@app.route('/api/ai/execute-code', methods=['POST'])
@login_required 
def api_ai_execute_code():
    """AI가 생성한 코드를 커널에서 실행"""
    try:
        data = request.get_json()
        code = data.get('code', '')
        kernel_id = data.get('kernel_id')
        auto_add_to_notebook = data.get('auto_add_to_notebook', False)
        
        if not code.strip():
            return jsonify({'success': False, 'error': '실행할 코드가 없습니다'})
        
        # 세션 커널 또는 지정된 커널에서 코드 실행
        if kernel_id:
            from LIBS.PAGE.kernel_manager import execute_kernel_code
            result = execute_kernel_code(kernel_id, code)
        else:
            from LIBS.PAGE.kernel_manager import execute_session_kernel_code_direct
            result = execute_session_kernel_code_direct(code)
        
        # 노트북에 자동 추가 옵션
        response = {
            'success': True,
            'result': result,
            'code': code,
            'auto_added': False
        }
        
        if auto_add_to_notebook and result.get('success'):
            # TODO: 노트북 셀에 코드 자동 추가 로직
            response['auto_added'] = True
        
        return jsonify(response)
        
    except Exception as e:
        log_message(f"AI 코드 실행 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'코드 실행 중 오류: {str(e)}'})

@app.route('/api/ai/analyze-error', methods=['POST'])
@login_required
def api_ai_analyze_error():
    """AI에게 에러 분석 및 수정 요청 (Mock AI 사용)"""
    try:
        data = request.get_json()
        error_message = data.get('error', '')
        code = data.get('code', '')
        context = data.get('context', '')
        chat_id = data.get('chat_id')
        
        if not error_message.strip():
            return jsonify({'success': False, 'error': '분석할 에러가 없습니다'})
        
        # 채팅 매니저에서 에러 분석 처리
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        
        # 채팅 ID가 없으면 새 채팅 생성
        if not chat_id:
            chat = chat_manager.create_chat(user_id, "🐛 에러 분석")
            chat_id = chat.id
        
        # 에러 분석 처리
        analysis_result = chat_manager.analyze_error(chat_id, error_message, code, context)
        
        if analysis_result['success']:
            return jsonify({
                'success': True,
                'analysis': analysis_result['analysis'],
                'suggested_fix': analysis_result.get('suggested_fix', ''),
                'fixed_code': analysis_result.get('fixed_code', ''),
                'chat_id': chat_id
            })
        else:
            return jsonify({'success': False, 'error': analysis_result.get('error', '에러 분석 실패')})
        
    except Exception as e:
        log_message(f"AI 에러 분석 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'에러 분석 중 오류: {str(e)}'})

# 채팅 관리 API 엔드포인트들
@app.route('/api/chats', methods=['GET'])
@login_required
def api_get_chats():
    """사용자의 채팅 목록 조회"""
    try:
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        chats = chat_manager.get_user_chats(user_id)
        
        # 채팅 데이터를 JSON 형태로 변환
        chat_list = []
        for chat in chats:
            chat_list.append({
                'id': chat.id,
                'title': chat.title,
                'preview': chat.get_last_message_preview(),
                'timestamp': chat.updated_at.strftime('%m월 %d일 %H:%M'),
                'messageCount': len(chat.messages),
                'active': chat.active
            })
        
        return jsonify({
            'success': True,
            'chats': chat_list,
            'count': len(chat_list)
        })
        
    except Exception as e:
        log_message(f"채팅 목록 조회 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'채팅 목록 조회 중 오류: {str(e)}'})

@app.route('/api/chats', methods=['POST'])
@login_required
def api_create_chat():
    """새 채팅 생성"""
    try:
        data = request.get_json()
        title = data.get('title', '새 채팅')
        
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        chat = chat_manager.create_chat(user_id, title)
        
        return jsonify({
            'success': True,
            'chat': {
                'id': chat.id,
                'title': chat.title,
                'preview': '새로운 대화를 시작하세요!',
                'timestamp': chat.created_at.strftime('%m월 %d일 %H:%M'),
                'messageCount': 0,
                'active': True
            }
        })
        
    except Exception as e:
        log_message(f"채팅 생성 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'채팅 생성 중 오류: {str(e)}'})

@app.route('/api/chats/<chat_id>', methods=['GET'])
@login_required
def api_get_chat(chat_id):
    """특정 채팅 조회"""
    try:
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        chat = chat_manager.get_chat(chat_id)
        
        if not chat or chat.user_id != user_id:
            return jsonify({'success': False, 'error': '채팅을 찾을 수 없습니다'}), 404
        
        # 메시지 데이터 변환
        messages = []
        for msg in chat.messages:
            messages.append({
                'id': msg['id'],
                'type': msg['type'],
                'content': msg['content'],
                'code_blocks': msg.get('code_blocks', []),
                'timestamp': msg['timestamp'].strftime('%H:%M'),
                'edited': msg.get('edited', False)
            })
        
        return jsonify({
            'success': True,
            'chat': {
                'id': chat.id,
                'title': chat.title,
                'messages': messages,
                'stats': chat.stats
            }
        })
            
    except Exception as e:
        log_message(f"채팅 조회 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'채팅 조회 중 오류: {str(e)}'})

@app.route('/api/chats/<chat_id>/activate', methods=['POST'])
@login_required  
def api_activate_chat(chat_id):
    """채팅 활성화"""
    try:
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        success = chat_manager.set_active_chat(user_id, chat_id)
        
        if success:
            return jsonify({'success': True, 'message': '채팅이 활성화되었습니다'})
        else:
            return jsonify({'success': False, 'error': '채팅 활성화 실패'}), 400
        
    except Exception as e:
        log_message(f"채팅 활성화 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'채팅 활성화 중 오류: {str(e)}'})

@app.route('/api/chats/<chat_id>', methods=['DELETE'])
@login_required
def api_delete_chat(chat_id):
    """채팅 삭제"""
    try:
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        success = chat_manager.delete_chat(chat_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': '채팅이 삭제되었습니다'})
        else:
            return jsonify({'success': False, 'error': '채팅 삭제 실패'}), 400
        
    except Exception as e:
        log_message(f"채팅 삭제 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'채팅 삭제 중 오류: {str(e)}'})

@app.route('/api/chats/search', methods=['GET'])
@login_required
def api_search_chats():
    """채팅 검색"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        
        if not query.strip():
            return jsonify({'success': False, 'error': '검색어가 필요합니다'})
        
        from CLASS.CLASS_chat_manager import get_chat_manager
        chat_manager = get_chat_manager()
        
        user_id = session.get('user_id', 'anonymous')
        results = chat_manager.search_chats(user_id, query, limit)
        
        # 검색 결과 변환
        chat_list = []
        for chat in results:
            chat_list.append({
                'id': chat.id,
                'title': chat.title,
                'preview': chat.get_last_message_preview(),
                'timestamp': chat.updated_at.strftime('%m월 %d일 %H:%M'),
                'messageCount': len(chat.messages),
                'active': chat.active
            })
        
        return jsonify({
            'success': True,
            'results': chat_list,
            'count': len(chat_list),
            'query': query
        })
        
    except Exception as e:
        log_message(f"채팅 검색 오류: {str(e)}")
        return jsonify({'success': False, 'error': f'채팅 검색 중 오류: {str(e)}'})

# 이미지 서빙 엔드포인트 (호환성을 위해 유지, 하지만 data URI 변환이 우선 사용됨)
@app.route('/img/<path:image_path>')
@login_required  
def serve_selenium_image(image_path):
    """Selenium으로 로드한 페이지의 이미지들을 서빙"""
    try:
        # 세션 커널에서 SYSTEM_SELENIUM 정보 가져오기
        from LIBS.PAGE.kernel_manager import get_session_kernel
        kernel = get_session_kernel()
        
        if kernel:
            namespace = kernel.get_namespace()
            shared_dict = namespace.get('shared_dict', {})
            
            if 'SYSTEM_SELENIUM' in shared_dict:
                selenium_data = shared_dict['SYSTEM_SELENIUM']
                if 'url' in selenium_data:
                    current_url = selenium_data['url']
                    
                    # 상대 경로를 절대 경로로 변환
                    from urllib.parse import urljoin
                    absolute_url = urljoin(current_url, image_path)
                    
                    # 이미지 다운로드
                    import requests
                    response = requests.get(absolute_url, timeout=10)
                    
                    if response.status_code == 200:
                        # Content-Type 결정
                        content_type = response.headers.get('content-type', 'image/jpeg')
                        if not content_type.startswith('image/'):
                            # 파일 확장자로 Content-Type 추정
                            if image_path.lower().endswith('.png'):
                                content_type = 'image/png'
                            elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
                                content_type = 'image/jpeg'
                            elif image_path.lower().endswith('.gif'):
                                content_type = 'image/gif'
                            elif image_path.lower().endswith('.svg'):
                                content_type = 'image/svg+xml'
                            else:
                                content_type = 'image/jpeg'
                        
                        from flask import Response
                        return Response(response.content, mimetype=content_type)
        
        # 기본 404 응답
        from flask import abort
        abort(404)
        
    except Exception as e:
        print(f"이미지 서빙 오류: {image_path} - {str(e)}")
        from flask import abort
        abort(404)




if __name__ == '__main__':
    log_message('system_info', 'Paramita AI를 시작합니다...')
    
    # 앱 시작 시 기존 커널 복원
    try:
        from LIBS.PAGE.kernel_manager import restore_existing_kernels
        restore_existing_kernels()
    except Exception as e:
        log_message('system_error', f'기존 커널 복원 중 오류: {str(e)}')
    
    log_message('system_info', '📓 Paramita AI: http://localhost:53301/notebook')
    log_message('system_info', '🐍 Python 커널: http://localhost:53301/kernel')
    log_message('system_info', '🏠 메인 페이지: http://localhost:53301/')
    app.run(debug=True, host='0.0.0.0', port=53301) 