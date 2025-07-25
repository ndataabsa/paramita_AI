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
            'attribute': {'name': '속성으로 찾기', 'params': ['find_attribute', 'find_item', 'find_range']}
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

CSS_EXTRACT_JS = """
var css_list = [];
var styleSheets = document.styleSheets;

for (var i = 0; i < styleSheets.length; i++) {
    try {
        var sheet = styleSheets[i];
        var rules = sheet.cssRules || sheet.rules;
        var cssText = '';
        
        if (rules) {
            for (var j = 0; j < rules.length; j++) {
                cssText += rules[j].cssText + '\\n';
            }
        }
        
        if (cssText.trim()) {
            css_list.push({
                'content': cssText,
                'url': sheet.href || 'inline'
            });
        }
    } catch (e) {}
}
return css_list;
"""

# 이미지 URL 수집 JavaScript 코드
IMAGE_EXTRACT_JS = """
var imgData = [];
var dataBgUrls = [];
var cssBackgroundUrls = [];

// img 태그 처리
var imgs = document.querySelectorAll('img[src]');
for (var i = 0; i < imgs.length; i++) {
    var originalSrc = imgs[i].getAttribute('src');  // 원본 속성값
    var absoluteSrc = imgs[i].src;  // 절대 URL
    if (absoluteSrc && !absoluteSrc.startsWith('data:')) {
        imgData.push({
            original: originalSrc,  // HTML에서 교체할 원본값
            absolute: absoluteSrc   // 다운로드할 절대 URL
        });
    }
}

// data-bg 속성 처리
var dataBgElements = document.querySelectorAll('[data-bg]');
for (var i = 0; i < dataBgElements.length; i++) {
    var dataBg = dataBgElements[i].getAttribute('data-bg');
    if (dataBg && !dataBg.startsWith('data:')) {
        dataBgUrls.push(dataBg);
    }
}

// CSS background-image 처리
var allElements = document.querySelectorAll('*');
for (var i = 0; i < allElements.length; i++) {
    var style = window.getComputedStyle(allElements[i]);
    var bgImage = style.backgroundImage;
    if (bgImage && bgImage !== 'none') {
        var urlMatch = bgImage.match(/url\\s*\\(\\s*["']?([^"'\\)]*)["']?\\s*\\)/);
        if (urlMatch && urlMatch[1]) {
            var originalUrl = urlMatch[1];
            if (!originalUrl.startsWith('data:') && !originalUrl.startsWith('http')) {
                // 상대 경로를 절대 경로로 변환
                var absoluteUrl = new URL(originalUrl, window.location.href).href;
                cssBackgroundUrls.push({
                    original: originalUrl,
                    absolute: absoluteUrl
                });
            } else if (originalUrl.startsWith('http') && !originalUrl.startsWith('data:')) {
                cssBackgroundUrls.push({
                    original: originalUrl,
                    absolute: originalUrl
                });
            }
        }
    }
}

return {imgData: imgData, dataBgUrls: dataBgUrls, cssBackgroundUrls: cssBackgroundUrls};
"""

WEBFONT_PROCESS_CODE = '''
            print("웹폰트 처리 시작...")
            
            processed_css_list = []
            webfont_count = 0
            webfont_extensions = ['.woff2', '.woff', '.ttf', '.eot', '.otf']
            
            for css_item in css_list:
                css_content = css_item.get('content', '')
                css_url = css_item.get('url', 'inline')
                
                if not css_content:
                    processed_css_list.append(css_item)
                    continue
                
                processed_content = css_content
                url_pattern = r"url\\s*\\([\\\"']?([^\\)]+?)[\\\"']?\\)"
                url_matches = re.findall(url_pattern, css_content, re.IGNORECASE)
                
                for url_match in url_matches:
                    is_webfont = any(url_match.lower().endswith(ext) for ext in webfont_extensions)
                    
                    if is_webfont:
                        try:
                            if css_url != 'inline' and not url_match.startswith(('http://', 'https://')):
                                if css_url.startswith('http'):
                                    absolute_font_url = urljoin(css_url, url_match)
                                else:
                                    absolute_font_url = urljoin(current_url, url_match)
                            elif url_match.startswith(('http://', 'https://')):
                                absolute_font_url = url_match
                            else:
                                absolute_font_url = urljoin(current_url, url_match)
                            
                            print(f"웹폰트 다운로드 중: {absolute_font_url}")
                            response = requests.get(absolute_font_url, timeout=10)
                            
                            if response.status_code == 200:
                                content_type = response.headers.get('content-type', '')
                                if not content_type:
                                    if url_match.endswith('.woff2'):
                                        content_type = 'font/woff2'
                                    elif url_match.endswith('.woff'):
                                        content_type = 'font/woff'
                                    elif url_match.endswith('.ttf'):
                                        content_type = 'font/ttf'
                                    elif url_match.endswith('.eot'):
                                        content_type = 'application/vnd.ms-fontobject'
                                    elif url_match.endswith('.otf'):
                                        content_type = 'font/otf'
                                    else:
                                        content_type = 'font/woff2'
                                
                                font_base64 = base64.b64encode(response.content).decode('utf-8')
                                data_uri = f"data:{content_type};base64,{font_base64}"
                                
                                patterns_to_replace = [
                                    f'url("{url_match}")',
                                    f"url(\\'{url_match}\\')",
                                    f'url({url_match})'
                                ]
                                
                                for pattern in patterns_to_replace:
                                    if pattern in processed_content:
                                        processed_content = processed_content.replace(pattern, f'url("{data_uri}")')
                                
                                webfont_count += 1
                                print(f"웹폰트 변환 완료: {url_match} -> data URI ({len(font_base64)//1024}KB)")
                            else:
                                print(f"웹폰트 다운로드 실패: {absolute_font_url} (HTTP {response.status_code})")
                        except Exception as e:
                            print(f"웹폰트 처리 실패: {url_match} - {str(e)}")
                            continue
                
                processed_item = css_item.copy()
                processed_item['content'] = processed_content
                processed_css_list.append(processed_item)
            
            if webfont_count > 0:
                print(f"웹폰트 처리 완료: {webfont_count}개 변환됨")
                css_list = processed_css_list
            else:
                print("웹폰트가 발견되지 않았습니다.")
'''

# 이미지 처리 Python 코드
IMAGE_PROCESS_CODE = f'''
            print("이미지 처리 시작...")
            
            image_js_code = {json.dumps(IMAGE_EXTRACT_JS)}
            img_result = driver.execute_script(image_js_code)
            
            if img_result:
                processed_html = page_source
                success_count = 0
                
                # img 태그 처리 (개수 제한 제거)
                for img_item in img_result.get('imgData', []):
                    try:
                        original_src = img_item['original']  # HTML에서 교체할 원본값
                        absolute_url = img_item['absolute']  # 다운로드할 절대 URL
                        
                        response = requests.get(absolute_url, timeout=5)
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            img_base64 = base64.b64encode(response.content).decode('utf-8')
                            data_uri = f"data:{{content_type}};base64,{{img_base64}}"
                            
                            # 원본 src 값으로 교체
                            processed_html = processed_html.replace(f'src="{{original_src}}"', f'src="{{data_uri}}"')
                            processed_html = processed_html.replace(f"src='{{original_src}}'", f"src='{{data_uri}}'")
                            
                            success_count += 1
                            print(f"이미지 변환 완료: {{original_src}} -> {{absolute_url[:50]}}...")
                            
                    except Exception as e:
                        print(f"이미지 처리 실패: {{absolute_url[:50]}}... - {{str(e)}}")
                        continue
                
                # data-bg 속성 처리
                for bg_url in img_result.get('dataBgUrls', [])[:5]:
                    try:
                        absolute_url = urljoin(current_url, bg_url)
                        response = requests.get(absolute_url, timeout=5)
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            img_base64 = base64.b64encode(response.content).decode('utf-8')
                            data_uri = f"data:{{content_type}};base64,{{img_base64}}"
                            
                            processed_html = processed_html.replace(f'data-bg="{{bg_url}}"', f'data-bg="{{data_uri}}"')
                            processed_html = processed_html.replace(f"data-bg='{{bg_url}}'", f"data-bg='{{data_uri}}'")
                            
                            success_count += 1
                            print(f"이미지 변환 완료: data_bg - {{bg_url[:50]}}...")
                            
                    except Exception as e:
                        print(f"데이터 배경 처리 실패: {{bg_url[:50]}}... - {{str(e)}}")
                        continue
                
                # CSS background-image 처리
                for css_bg_item in img_result.get('cssBackgroundUrls', []):
                    try:
                        original_url = css_bg_item['original']
                        absolute_url = css_bg_item['absolute']
                        
                        response = requests.get(absolute_url, timeout=5)
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            img_base64 = base64.b64encode(response.content).decode('utf-8')
                            data_uri = f"data:{{content_type}};base64,{{img_base64}}"
                            
                            # CSS에서 background-image URL 교체
                            processed_html = processed_html.replace(f'url("{{original_url}}")', f'url("{{data_uri}}")')
                            processed_html = processed_html.replace(f"url('{{original_url}}')", f"url('{{data_uri}}')")
                            processed_html = processed_html.replace(f'url({{original_url}})', f'url({{data_uri}})')
                            
                            success_count += 1
                            print(f"CSS 배경 이미지 변환 완료: {{original_url}} -> {{absolute_url[:50]}}...")
                            
                    except Exception as e:
                        print(f"CSS 배경 이미지 처리 실패: {{absolute_url[:50]}}... - {{str(e)}}")
                        continue
                
                # CSS 리스트에서도 background-image 처리
                css_success_count = 0
                for css_item in css_list:
                    if css_item and 'content' in css_item and css_item['content']:
                        original_css = css_item['content']
                        
                        # CSS에서 background-image URL들 찾아서 교체
                        for css_bg_item in img_result.get('cssBackgroundUrls', []):
                            original_url = css_bg_item['original']
                            absolute_url = css_bg_item['absolute']
                            
                            # 이미 다운로드된 이미지라면 base64로 교체
                            if f'url("{{original_url}}")' in original_css or f"url('{{original_url}}')" in original_css or f'url({{original_url}})' in original_css:
                                try:
                                    response = requests.get(absolute_url, timeout=5)
                                    if response.status_code == 200:
                                        content_type = response.headers.get('content-type', 'image/jpeg')
                                        img_base64 = base64.b64encode(response.content).decode('utf-8')
                                        data_uri = f"data:{{content_type}};base64,{{img_base64}}"
                                        
                                        # CSS에서 URL 교체
                                        css_item['content'] = css_item['content'].replace(f'url("{{original_url}}")', f'url("{{data_uri}}")')
                                        css_item['content'] = css_item['content'].replace(f"url('{{original_url}}')", f"url('{{data_uri}}')")
                                        css_item['content'] = css_item['content'].replace(f'url({{original_url}})', f'url({{data_uri}})')
                                        
                                        css_success_count += 1
                                        print(f"CSS 내부 배경 이미지 변환: {{original_url}}")
                                except:
                                    continue
                
                if css_success_count > 0:
                    print(f"CSS에서 {{css_success_count}}개 background-image를 base64로 변환했습니다.")
                
                if success_count > 0:
                    page_source = processed_html
                    print(f"이미지 {{success_count}}개를 base64로 변환하여 HTML에 포함했습니다.")
                else:
                    print("이미지 변환에 실패했습니다.")
            else:
                print("이미지가 발견되지 않았습니다.")
'''

SELENIUM_REFRESH_CODE = f"""
import re
import requests
import base64
from urllib.parse import urljoin
import json
try:
    if 'shared_dict' in globals() and 'SYSTEM_SELENIUM' in shared_dict:
        selenium_data = shared_dict['SYSTEM_SELENIUM']
        if 'driver' in selenium_data:
            driver = selenium_data['driver']
            page_source = driver.page_source
            current_url = driver.current_url
            css_js_code = {json.dumps(CSS_EXTRACT_JS)}
            css_list = driver.execute_script(css_js_code)
            if not css_list:
                css_list = []

            print(f"CSS 추출 완료: {{len(css_list)}}개")
            # 웹폰트 처리 실행
            {WEBFONT_PROCESS_CODE}
            
            # 이미지 처리 실행
            {IMAGE_PROCESS_CODE}

            css_json_string = json.dumps(css_list, ensure_ascii=False)
            result_data = {{
                'html': page_source,
                'css': css_json_string,
                'url': current_url,
                'driver': driver
            }}
            shared_dict['SYSTEM_SELENIUM'] = result_data
            print(f"HTML 뷰어 새로고침 성공:")
            print(f"  - HTML 길이: {{len(page_source)}}")
            print(f"  - CSS 파일 개수: {{len(css_list)}}")
            print(f"  - URL: {{current_url}}")
            # 디버깅: 실제 data URI 이미지 개수 확인
            data_uri_count = page_source.count('src="data:image')
            data_bg_count = page_source.count('data-bg="data:image')
            css_bg_count = page_source.count('background-image: url("data:image')
            print(f"  - data URI 이미지 개수: img src={{data_uri_count}}, data-bg={{data_bg_count}}, css bg={{css_bg_count}}")
        else:
            print("Driver가 없습니다.")
    else:
        print("SYSTEM_SELENIUM 데이터가 없습니다.")
except Exception as e:
    print(f"새로고침 실패: {{str(e)}}")
"""

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

# NP Notebook 페이지
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
        
        if not kernel_id:
            return jsonify({'success': False, 'error': '커널 ID가 필요합니다'})
        
        # 새로고침 코드를 해당 커널에서 실행
        refresh_code = SELENIUM_REFRESH_CODE
        
        # 직접 kernel manager 함수 호출 (HTTP 요청 대신)
        from LIBS.PAGE.kernel_manager import CLASS_kernel_manager
        
        try:
            print(f"커널 ID: {kernel_id}")
            print(f"실행할 코드 길이: {len(refresh_code)} 문자")
            
            result = CLASS_kernel_manager.execute_code(kernel_id, refresh_code, 30.0)
            
            print(f"커널 실행 결과: {result}")
            print(f"결과 타입: {type(result)}")
            
            if result and result.get('success', True):  # 성공으로 간주
                return jsonify({'success': True, 'message': 'SYSTEM_SELENIUM 데이터가 새로고침되었습니다'})
            else:
                return jsonify({'success': False, 'error': '커널 실행 실패', 'details': result})
        except Exception as e:
            print(f"커널 실행 예외: {str(e)}")
            print(f"예외 타입: {type(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'커널 실행 오류: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'API 오류: {str(e)}'})

# 이미지 서빙 엔드포인트 (커널 ID별 격리)
@app.route('/img/<kernel_id>/<path:image_path>')
@login_required  
def serve_selenium_image(kernel_id, image_path):
    """Selenium으로 로드한 페이지의 이미지들을 서빙 (커널별 격리)"""
    try:
        # 커널 ID 검증 및 해당 커널의 데이터 확인
        from LIBS.PAGE.kernel_manager import CLASS_kernel_manager
        if not CLASS_kernel_manager.kernel_exists(kernel_id):
            from flask import abort
            abort(404)
        
        # shared_dict에서 SYSTEM_SELENIUM 정보 가져오기
        if 'SYSTEM_SELENIUM' in shared_dict:
            selenium_data = shared_dict['SYSTEM_SELENIUM']
            if 'url' in selenium_data:
                current_url = selenium_data['url']
                
                # 상대 경로를 절대 경로로 변환
                from urllib.parse import urljoin
                absolute_url = urljoin(current_url, f'img/{image_path}')
                
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

# 기존 이미지 경로 호환성 (임시)
@app.route('/img/<path:image_path>')
@login_required  
def serve_legacy_image(image_path):
    """기존 이미지 경로 호환성을 위한 임시 라우트"""
    try:
        # shared_dict에서 SYSTEM_SELENIUM 정보 가져오기
        if 'SYSTEM_SELENIUM' in shared_dict:
            selenium_data = shared_dict['SYSTEM_SELENIUM']
            if 'url' in selenium_data:
                current_url = selenium_data['url']
                
                # 상대 경로를 절대 경로로 변환
                from urllib.parse import urljoin
                absolute_url = urljoin(current_url, f'img/{image_path}')
                
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
    log_message('system_info', 'NP Notebook을 시작합니다...')
    
    # 앱 시작 시 기존 커널 복원
    try:
        from LIBS.PAGE.kernel_manager import restore_existing_kernels
        restore_existing_kernels()
    except Exception as e:
        log_message('system_error', f'기존 커널 복원 중 오류: {str(e)}')
    
    log_message('system_info', '📓 NP Notebook: http://localhost:53301/notebook')
    log_message('system_info', '🐍 Python 커널: http://localhost:53301/kernel')
    log_message('system_info', '🏠 메인 페이지: http://localhost:53301/')
    app.run(debug=True, host='0.0.0.0', port=53301) 