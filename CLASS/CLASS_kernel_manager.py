import json
import uuid
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
import sys
import io
import contextlib
import psutil
import os
from MODULE.module_logger import log_message

class KernelManager:
    """
    Python 커널 관리자
    여러 커널을 생성, 관리, 종료하는 기능을 제공합니다.
    """
    
    def __init__(self):
        self.kernels = {}  # kernel_id -> Kernel 객체
        self.lock = threading.Lock()
        self.file_kernel_mapping = {}  # file_path -> kernel_id
        self.file_user_kernel_mapping = {}  # (file_path, user_id) -> kernel_id
        self.session_kernel = None  # 세션 커널 (job 페이지용)
        self.process_kernels = {}  # pid -> kernel_id (프로세스 기반 커널)
    
    def scan_process_kernels(self):
        """실행 중인 Python 프로세스들을 스캔하여 커널로 인식합니다."""
        try:
            current_pid = os.getpid()
            
            # 현재 프로세스의 부모 프로세스도 확인
            try:
                current_process = psutil.Process(current_pid)
                parent_pid = current_process.ppid()
            except:
                parent_pid = None
            
            # 기존 프로세스 커널들 모두 제거
            with self.lock:
                process_kernels_to_remove = []
                for kernel_id in list(self.kernels.keys()):
                    if kernel_id.startswith('process_kernel_'):
                        process_kernels_to_remove.append(kernel_id)
                
                for kernel_id in process_kernels_to_remove:
                    pid = int(kernel_id.replace('process_kernel_', ''))
                    if pid in self.process_kernels:
                        del self.process_kernels[pid]
                    del self.kernels[kernel_id]
            
            # 모든 Python 프로세스 찾기
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        pid = proc.info['pid']
                        # 현재 프로세스와 부모 프로세스는 제외
                        if pid != current_pid and pid != parent_pid:
                            python_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 각 프로세스를 커널로 등록
            for proc_info in python_processes:
                pid = proc_info['pid']
                cmdline = proc_info['cmdline'] or []
                
                # 커널 관련 프로세스인지 확인
                if self._is_kernel_process(cmdline):
                    kernel_id = f"process_kernel_{pid}"
                    self.process_kernels[pid] = kernel_id
                    
                    # 가상 커널 객체 생성 (실제 커널이 아닌 프로세스 정보만)
                    self.kernels[kernel_id] = ProcessKernel(kernel_id, pid, proc_info)
            
        except Exception as e:
            print(f"프로세스 커널 스캔 오류: {str(e)}")
    
    def _is_kernel_process(self, cmdline: List[str]) -> bool:
        """프로세스가 커널 관련 프로세스인지 확인합니다."""
        if not cmdline:
            return False
        
        cmd_str = ' '.join(cmdline).lower()
        
        # Flask 서버나 주요 시스템 프로세스 제외
        exclude_keywords = [
            'flask', 'jupyapp.py', 'main.py', 'app.py', 'server.py',
            'gunicorn', 'uwsgi', 'nginx', 'apache', 'systemd',
            'python -m', 'python -c', 'python -u'
        ]
        
        for exclude_keyword in exclude_keywords:
            if exclude_keyword in cmd_str:
                return False
        
        # 실제 커널 관련 프로세스만 허용
        kernel_keywords = [
            'jupyter', 'ipython', 'kernel', 'notebook'
        ]
        
        # 커널 관련 키워드 확인
        for keyword in kernel_keywords:
            if keyword in cmd_str:
                return True
        
        # Python 스크립트 실행 중인지 확인 (더 엄격하게)
        if len(cmdline) > 1 and cmdline[1].endswith('.py'):
            # Flask나 서버 관련 스크립트는 제외
            script_name = cmdline[1].lower()
            if any(exclude in script_name for exclude in ['flask', 'server', 'app', 'main']):
                return False
            return True
        
        return False
    
    def get_process_kernel_status(self, kernel_id: str) -> Dict[str, Any]:
        """프로세스 커널의 상태를 반환합니다."""
        if not kernel_id.startswith('process_kernel_'):
            return {'status': 'not_found'}
        
        try:
            pid = int(kernel_id.replace('process_kernel_', ''))
            process = psutil.Process(pid)
            
            if process.is_running():
                # 사용자 정보 가져오기
                try:
                    username = process.username()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    username = "Unknown"
                
                return {
                    'status': 'running',
                    'pid': pid,
                    'username': username,
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                    'cmdline': process.cmdline()
                }
            else:
                return {'status': 'terminated'}
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            return {'status': 'not_found'}
    
    def terminate_process_kernel(self, kernel_id: str) -> bool:
        """프로세스 커널을 종료합니다."""
        if not kernel_id.startswith('process_kernel_'):
            return False
        
        try:
            pid = int(kernel_id.replace('process_kernel_', ''))
            process = psutil.Process(pid)
            
            if process.is_running():
                process.terminate()
                print(f"프로세스 커널 종료: PID {pid}")
                
                # 커널 목록에서 제거
                with self.lock:
                    if kernel_id in self.kernels:
                        del self.kernels[kernel_id]
                    if pid in self.process_kernels:
                        del self.process_kernels[pid]
                
                return True
            else:
                return False
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            return False
    
    def create_kernel(self, kernel_id: str) -> str:
        """새로운 커널을 생성합니다."""
        with self.lock:
            if kernel_id in self.kernels:
                # 기존 커널이 있으면 삭제 후 새로 생성
                old_kernel = self.kernels.pop(kernel_id)
                old_kernel.shutdown()
            
            try:
                self.kernels[kernel_id] = Kernel(kernel_id)
                return kernel_id
            except Exception as e:
                print(f"커널 생성 실패: {kernel_id}, 오류: {str(e)}")
                log_message('kernel_error', f'커널 {kernel_id} 생성 실패: {str(e)}')
                import traceback
                traceback.print_exc()
                raise
    
    def get_kernel(self, kernel_id: str) -> Optional['Kernel']:
        """커널을 가져옵니다."""
        with self.lock:
            result = self.kernels.get(kernel_id)
            return result
    
    def delete_kernel(self, kernel_id: str) -> bool:
        """커널을 삭제합니다."""
        if kernel_id.startswith('process_kernel_'):
            return self.terminate_process_kernel(kernel_id)
        
        with self.lock:
            if kernel_id in self.kernels:
                kernel = self.kernels.pop(kernel_id)
                kernel.shutdown()
                return True
            return False
    
    def get_all_kernels(self) -> Dict[str, 'Kernel']:
        """모든 커널을 가져옵니다."""
        with self.lock:
            return self.kernels.copy()
    
    def list_kernels(self) -> List[str]:
        """모든 커널 ID 목록을 반환합니다."""
        with self.lock:
            return list(self.kernels.keys())
    
    def get_kernel_status(self, kernel_id: str) -> Dict[str, Any]:
        """커널 상태를 반환합니다."""
        if kernel_id.startswith('process_kernel_'):
            return self.get_process_kernel_status(kernel_id)
        
        kernel = self.get_kernel(kernel_id)
        if kernel is None:
            return {'status': 'not_found'}
        
        return {
            'kernel_id': kernel.kernel_id,
            'status': 'idle' if not kernel.is_shutdown else 'shutdown',
            'remaining_time': kernel.get_remaining_time(),
            'timeout_hours': kernel.timeout_hours,
            'expiry_time': kernel.expiry_time.isoformat()
        }
    
    def execute_code(self, kernel_id: str, code: str, timeout: float = 30.0) -> Dict[str, Any]:
        """커널에서 코드를 실행합니다."""
        kernel = self.get_kernel(kernel_id)
        if kernel is None:
            return {
                'success': False,
                'error': f"커널 '{kernel_id}'를 찾을 수 없습니다"
            }
        
        try:
            result = kernel.execute(code, int(timeout))
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def shutdown_all(self):
        """모든 커널을 종료합니다."""
        with self.lock:
            for kernel in self.kernels.values():
                try:
                    kernel.shutdown()
                except Exception as e:
                    log_message('kernel_error', f'커널 종료 중 오류: {str(e)}')
            self.kernels.clear()
            self.file_kernel_mapping.clear()
    
    def set_file_kernel_mapping(self, file_path: str, kernel_id: str):
        """파일과 커널의 매핑을 설정합니다."""
        with self.lock:
            self.file_kernel_mapping[file_path] = kernel_id
    
    def get_file_kernel_mapping(self, file_path: str) -> Optional[str]:
        """파일과 매핑된 커널 ID를 가져옵니다."""
        with self.lock:
            return self.file_kernel_mapping.get(file_path)
    
    def remove_file_kernel_mapping(self, file_path: str) -> Optional[str]:
        """파일과 커널의 매핑을 제거합니다."""
        with self.lock:
            if file_path in self.file_kernel_mapping:
                kernel_id = self.file_kernel_mapping[file_path]
                del self.file_kernel_mapping[file_path]
                return kernel_id
            return None
    
    def get_all_file_kernel_mappings(self) -> Dict[str, str]:
        """모든 파일-커널 매핑을 가져옵니다."""
        with self.lock:
            return self.file_kernel_mapping.copy()
    
    def get_all_file_user_kernel_mappings(self) -> Dict[Tuple[str, str], str]:
        """모든 파일-사용자-커널 매핑을 가져옵니다."""
        with self.lock:
            return self.file_user_kernel_mapping.copy()
    
    def set_file_user_kernel_mapping(self, file_path: str, user_id: str, kernel_id: str):
        """파일 경로와 사용자 ID에 대한 커널 매핑을 설정합니다."""
        with self.lock:
            key = (file_path, user_id)
            self.file_user_kernel_mapping[key] = kernel_id
        
        # lock 밖에서 커널에 파일 정보 저장 (데드락 방지)
        try:
            kernel = self.get_kernel(kernel_id)
            if kernel:
                kernel.set_file_user_info(file_path, user_id)
        except Exception as e:
            print(f"커널 조회 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def get_file_user_kernel_mapping(self, file_path: str, user_id: str) -> Optional[str]:
        """파일 경로와 사용자 ID에 대한 커널 ID를 가져옵니다."""
        with self.lock:
            key = (file_path, user_id)
            result = self.file_user_kernel_mapping.get(key)
            return result
    
    def remove_file_user_kernel_mapping(self, file_path: str, user_id: str) -> Optional[str]:
        """파일 경로와 사용자 ID에 대한 커널 매핑을 제거합니다."""
        with self.lock:
            key = (file_path, user_id)
            kernel_id = self.file_user_kernel_mapping.pop(key, None)
            return kernel_id
    
    def restore_file_user_mappings(self):
        """기존 커널들에서 파일 경로와 사용자 ID 정보를 복원합니다."""
        restored_mappings = {}
        
        with self.lock:
            for kernel_id, kernel in self.kernels.items():
                try:
                    file_path, user_id = kernel.get_file_user_info()
                    if file_path and user_id:
                        key = (file_path, user_id)
                        self.file_user_kernel_mapping[key] = kernel_id
                        restored_mappings[key] = kernel_id
                        print(f"커널 매핑 복원: 파일 {file_path}, 사용자 {user_id} -> 커널 {kernel_id}")
                except Exception as e:
                    print(f"커널 {kernel_id}에서 파일 정보 복원 실패: {str(e)}")
                    continue
        
        return restored_mappings
    
    def create_session_kernel(self) -> str:
        """세션 커널을 생성합니다."""
        with self.lock:
            if self.session_kernel is None:
                self.session_kernel = Kernel("session_kernel")
            return "session_kernel"
    
    def get_session_kernel(self) -> Optional['Kernel']:
        """세션 커널을 가져옵니다."""
        with self.lock:
            return self.session_kernel
    
    def shutdown_session_kernel(self):
        """세션 커널을 종료합니다."""
        with self.lock:
            if self.session_kernel:
                try:
                    self.session_kernel.shutdown()
                except Exception as e:
                    log_message('kernel_error', f'세션 커널 종료 중 오류: {str(e)}')
                self.session_kernel = None


class Kernel:
    """
    Python 커널 클래스
    Jupyter 커널과 유사한 기능을 제공합니다.
    """
    
    def __init__(self, kernel_id: str):
        try:
            self.kernel_id = kernel_id
            self.namespace = {}  # shared_dict를 직접 namespace로 사용
            self.history = []
            self.lock = threading.Lock()
            self.timeout_hours = 12  # 기본 12시간
            self.expiry_time = datetime.now() + timedelta(hours=self.timeout_hours)
            self.is_shutdown = False
            self.file_user_info = {} # 파일 경로와 사용자 ID 정보를 저장할 딕셔너리
            
            # 이미지 변환 최적화 관련 변수들
            self.html_conversion_init = False  # 처음 이미지 변환 완료 여부
            self.last_html_content = ""        # 이전 HTML 내용 (비교용)
            self.image_cache = {}              # 이미지 캐시 (URL -> data URI)
            
            # JavaScript 코드들 (기존 jupyapp.py에서 이동)
            self.CSS_EXTRACT_JS = """
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

            self.IMAGE_EXTRACT_JS = """
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
        var urlMatch = bgImage.match(/url\s*\(\s*["']?([^"')]*?)["']?\s*\)/);
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
        except Exception as e:
            print(f"Kernel 초기화 실패: {kernel_id}, 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """코드를 실행합니다."""
        if self.is_shutdown:
            raise RuntimeError("커널이 종료되었습니다.")
        
        # 시간제한 확인
        if datetime.now() > self.expiry_time:
            raise RuntimeError("커널 시간제한이 만료되었습니다.")
        
        try:
            import io
            import sys
            import contextlib
            
            print(f"=== 커널 실행 시작: {self.kernel_id} ===")
            print(f"실행할 코드: {code}")
            
            # 출력 캡처를 위한 StringIO 객체들
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # 실행 시작 시간
            start_time = datetime.now()
            
            print(f"=== 커널 실행 시작: {self.kernel_id} ===")
            print(f"실행할 코드: {code}")
            
            # stdout과 stderr를 캡처하면서 코드 실행
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                try:
                    # 코드 컴파일
                    compiled_code = compile(code, '<string>', 'exec')
                    
                    # 실행 전 네임스페이스 백업 (오류 발생 시 복구용)
                    namespace_backup = self.namespace.copy()
                    
                    # 코드 실행
                    exec(compiled_code, self.namespace)
                    
                except SyntaxError as e:
                    # 구문 오류 처리
                    raise SyntaxError(f"구문 오류: {str(e)}")
                except NameError as e:
                    # 이름 오류 처리 (변수/함수 미정의)
                    raise NameError(f"이름 오류: {str(e)}")
                except TypeError as e:
                    # 타입 오류 처리
                    raise TypeError(f"타입 오류: {str(e)}")
                except ValueError as e:
                    # 값 오류 처리
                    raise ValueError(f"값 오류: {str(e)}")
                except Exception as e:
                    # 기타 모든 오류 처리
                    # 네임스페이스 복구 시도
                    try:
                        self.namespace = namespace_backup
                    except:
                        pass
                    raise e
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 캡처된 출력 가져오기
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            print(f"stdout 캡처: {repr(stdout_output)}")
            print(f"stderr 캡처: {repr(stderr_output)}")
            
            # 실행 기록에 추가
            self.history.append({
                'code': code,
                'stdout': stdout_output,
                'stderr': stderr_output,
                'execution_time': execution_time,
                'timestamp': datetime.now()
            })
            
            result = {
                'success': True,
                'stdout': stdout_output,
                'stderr': stderr_output,
                'execution_time': execution_time,
                'execution_count': len(self.history)
            }
            

            
            return result
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            

            
            # 오류 발생 시에도 실행 기록에 추가
            self.history.append({
                'code': code,
                'stdout': '',
                'stderr': error_traceback,
                'execution_time': 0.0,
                'timestamp': datetime.now(),
                'error': str(e)
            })
            
            result = {
                'success': False,
                'stdout': '',
                'stderr': error_traceback,
                'error': str(e),
                'execution_time': 0.0,
                'execution_count': len(self.history)
            }
            

            
            return result
    
    def get_namespace(self) -> Dict[str, Any]:
        """네임스페이스를 가져옵니다."""
        with self.lock:
            return self.namespace.copy()
    
    def clear_namespace(self):
        """네임스페이스를 초기화합니다."""
        with self.lock:
            # shared_dict는 유지하고 나머지만 초기화
            shared_dict = self.namespace.get('shared_dict', {})
            self.namespace.clear()
            self.namespace['shared_dict'] = shared_dict
            self.history.clear()
    
    def refresh_selenium_with_data_conversion(self, scroll_x=0, scroll_y=0):
        """
        SYSTEM_SELENIUM 데이터를 새로고침하고 CSS와 이미지를 data URI로 변환합니다.
        HTML 뷰어에서 원본 페이지와 거의 비슷하게 표시되도록 처리합니다.
        스크롤 좌표가 주어지면 Selenium도 해당 위치로 스크롤합니다.
        """
        import json
        import requests
        import base64
        
        # 디버깅: 스크롤 좌표 수신 로깅
        print(f"🔍 refresh_selenium_with_data_conversion 호출됨")
        print(f"  - 스크롤 좌표: ({scroll_x}, {scroll_y})")
        
        try:
            with self.lock:
                shared_dict = self.namespace.get('shared_dict', {})
                
                if 'SYSTEM_SELENIUM' not in shared_dict:
                    return {'success': False, 'error': 'SYSTEM_SELENIUM 데이터가 없습니다.'}
                
                selenium_data = shared_dict['SYSTEM_SELENIUM']
                if 'driver' not in selenium_data:
                    return {'success': False, 'error': 'Driver가 없습니다.'}
                
                driver = selenium_data['driver']
                page_source = driver.page_source
                current_url = driver.current_url
                
                # CSS 추출
                css_list = driver.execute_script(self.CSS_EXTRACT_JS)
                if not css_list:
                    css_list = []
                
                print(f"CSS 추출 완료: {len(css_list)}개")
                
                # HTML 변경 감지 및 이미지 변환 최적화
                should_convert_images = True
                html_length_diff = 0
                
                if self.html_conversion_init and self.last_html_content:
                    # 이전 HTML과 비교하여 1000자 이상 차이나는지 확인
                    html_length_diff = abs(len(page_source) - len(self.last_html_content))
                    if html_length_diff < 1000:
                        should_convert_images = False
                        print(f"📝 HTML 변경량 적음 ({html_length_diff}자 차이) - 이미지 변환 건너뜀")
                    else:
                        print(f"📝 HTML 변경량 많음 ({html_length_diff}자 차이) - 이미지 재변환 필요")
                        self.html_conversion_init = False  # 다시 초기화하여 이미지 재변환
                else:
                    print("📝 첫 번째 이미지 변환 또는 초기화 필요")
                
                # 이미지 처리 (조건부 실행)
                img_result = driver.execute_script(self.IMAGE_EXTRACT_JS) if should_convert_images else None
                
                if img_result:
                    success_count = 0
                    
                    # 1. img 태그 처리 (캐시 최적화)
                    for img_item in img_result.get('imgData', []):
                        try:
                            original_src = img_item['original']
                            absolute_src = img_item['absolute']
                            
                            # 캐시에서 먼저 확인
                            data_uri = self.image_cache.get(absolute_src) or self.image_cache.get(original_src)
                            
                            if not data_uri:
                                # 캐시에 없으면 새로 다운로드
                                response = requests.get(absolute_src, timeout=5)
                                if response.status_code == 200:
                                    content_type = response.headers.get('content-type', 'image/jpeg')
                                    img_base64 = base64.b64encode(response.content).decode('utf-8')
                                    data_uri = f"data:{content_type};base64,{img_base64}"
                                    # 캐시에 저장
                                    self.image_cache[absolute_src] = data_uri
                                    self.image_cache[original_src] = data_uri
                                    print(f"이미지 다운로드: {original_src}")
                            else:
                                print(f"이미지 캐시 사용: {original_src}")
                            
                            if data_uri:
                                page_source = page_source.replace(f'src="{original_src}"', f'src="{data_uri}"')
                                page_source = page_source.replace(f"src='{original_src}'", f"src='{data_uri}'")
                                success_count += 1
                        except Exception as img_error:
                            print(f"이미지 처리 실패: {img_item.get('original', 'unknown')} - {str(img_error)}")
                            continue
                    
                    # 2. CSS background-image 처리 (HTML 인라인 스타일 포함, 캐시 최적화)
                    for bg_item in img_result.get('cssBackgroundUrls', []):
                        try:
                            original_url = bg_item['original']
                            absolute_url = bg_item['absolute']
                            
                            # 이미 처리된 배경 이미지인지 체크 (중복 방지)
                            if absolute_url in self.session_processed_urls:
                                print(f"HTML 배경 이미지 중복 건너뛰기: {original_url}")
                                continue
                            
                            self.session_processed_urls.add(absolute_url)
                            
                            # 캐시에서 먼저 확인
                            data_uri = self.image_cache.get(absolute_url) or self.image_cache.get(original_url)
                            
                            if not data_uri:
                                # 캐시에 없으면 새로 다운로드
                                response = requests.get(absolute_url, timeout=5)
                                if response.status_code == 200:
                                    content_type = response.headers.get('content-type', 'image/jpeg')
                                    img_base64 = base64.b64encode(response.content).decode('utf-8')
                                    data_uri = f"data:{content_type};base64,{img_base64}"
                                    # 캐시에 저장
                                    self.image_cache[absolute_url] = data_uri
                                    self.image_cache[original_url] = data_uri
                                    print(f"배경 이미지 다운로드: {original_url}")
                            else:
                                print(f"배경 이미지 캐시 사용: {original_url}")
                            
                            if data_uri:
                                # HTML에서 모든 형태의 background-image URL 교체
                                import re
                                # 다양한 패턴으로 URL 교체
                                patterns = [
                                    (f'url("{original_url}")', f'url("{data_uri}")'),
                                    (f"url('{original_url}')", f"url('{data_uri}')"),
                                    (f'url({original_url})', f'url("{data_uri}")'),
                                    # 공백이 있는 경우도 고려
                                    (f'url( "{original_url}" )', f'url("{data_uri}")'),
                                    (f"url( '{original_url}' )", f"url('{data_uri}')"),
                                    (f'url( {original_url} )', f'url("{data_uri}")'),
                                ]
                                
                                for old_pattern, new_pattern in patterns:
                                    if old_pattern in page_source:
                                        page_source = page_source.replace(old_pattern, new_pattern)
                                        print(f"배경 이미지 변환 (패턴): {old_pattern} -> {new_pattern}")
                                
                                # 정규식으로 더 복잡한 패턴도 처리
                                regex_patterns = [
                                    rf'url\s*\(\s*["\']?\s*{re.escape(original_url)}\s*["\']?\s*\)',
                                ]
                                
                                for pattern in regex_patterns:
                                    page_source = re.sub(pattern, f'url("{data_uri}")', page_source, flags=re.IGNORECASE)
                                
                                success_count += 1
                                print(f"배경 이미지 변환: {original_url}")
                        except Exception as bg_error:
                            print(f"배경 이미지 처리 실패: {bg_item.get('original', 'unknown')} - {str(bg_error)}")
                            continue
                    
                    # 3. data-bg 속성 처리 (캐시 최적화)
                    for data_bg_url in img_result.get('dataBgUrls', []):
                        try:
                            from urllib.parse import urljoin
                            absolute_url = urljoin(current_url, data_bg_url)
                            
                            # 캐시에서 먼저 확인
                            data_uri = self.image_cache.get(absolute_url) or self.image_cache.get(data_bg_url)
                            
                            if not data_uri:
                                # 캐시에 없으면 새로 다운로드
                                response = requests.get(absolute_url, timeout=5)
                                if response.status_code == 200:
                                    content_type = response.headers.get('content-type', 'image/jpeg')
                                    img_base64 = base64.b64encode(response.content).decode('utf-8')
                                    data_uri = f"data:{content_type};base64,{img_base64}"
                                    # 캐시에 저장
                                    self.image_cache[absolute_url] = data_uri
                                    self.image_cache[data_bg_url] = data_uri
                                    print(f"데이터 배경 이미지 다운로드: {data_bg_url}")
                            else:
                                print(f"데이터 배경 이미지 캐시 사용: {data_bg_url}")
                            
                            if data_uri:
                                # data-bg 속성 교체
                                page_source = page_source.replace(f'data-bg="{data_bg_url}"', f'data-bg="{data_uri}"')
                                page_source = page_source.replace(f"data-bg='{data_bg_url}'", f"data-bg='{data_uri}'")
                                
                                success_count += 1
                                print(f"데이터 배경 이미지 변환: {data_bg_url}")
                        except Exception as data_bg_error:
                            print(f"데이터 배경 이미지 처리 실패: {data_bg_url} - {str(data_bg_error)}")
                            continue
                    
                    print(f"총 이미지 {success_count}개 변환 완료")
                
                # 4. 이미지 캐시 활용 (기존 캐시 재사용)
                # self.image_cache 사용 (클래스 멤버변수)
                
                # 전체 변환 세션에서 처리된 모든 URL들을 추적 (중복 방지)
                if not hasattr(self, 'session_processed_urls'):
                    self.session_processed_urls = set()
                
                # HTML에서 다운로드한 이미지들을 캐시에 저장
                if img_result:
                    
                    for img_item in img_result.get('imgData', []):
                        original_src = img_item['original']
                        absolute_src = img_item['absolute']
                        
                        # 이미 처리된 이미지인지 체크
                        if absolute_src in self.session_processed_urls:
                            print(f"일반 이미지 중복 건너뛰기: {original_src}")
                            continue
                        
                        self.session_processed_urls.add(absolute_src)
                        
                        # 캐시에 이미 있는지 체크
                        if absolute_src in self.image_cache or original_src in self.image_cache:
                            print(f"일반 이미지 캐시 사용: {original_src}")
                            continue
                        
                        try:
                            response = requests.get(absolute_src, timeout=5)
                            if response.status_code == 200:
                                content_type = response.headers.get('content-type', 'image/jpeg')
                                img_base64 = base64.b64encode(response.content).decode('utf-8')
                                data_uri = f"data:{content_type};base64,{img_base64}"
                                self.image_cache[absolute_src] = data_uri
                                self.image_cache[original_src] = data_uri
                                print(f"일반 이미지 변환 완료: {original_src}")
                        except:
                            continue
                    
                    for bg_item in img_result.get('cssBackgroundUrls', []):
                        original_url = bg_item['original']
                        absolute_url = bg_item['absolute']
                        
                        # 이미 처리된 배경 이미지인지 체크
                        if absolute_url in self.session_processed_urls:
                            print(f"배경 이미지 중복 건너뛰기: {original_url}")
                            continue
                        
                        self.session_processed_urls.add(absolute_url)
                        
                        # 캐시에 이미 있는지 체크
                        if absolute_url in self.image_cache or original_url in self.image_cache:
                            print(f"배경 이미지 캐시 사용: {original_url}")
                            continue
                        
                        try:
                            response = requests.get(absolute_url, timeout=5)
                            if response.status_code == 200:
                                content_type = response.headers.get('content-type', 'image/jpeg')
                                img_base64 = base64.b64encode(response.content).decode('utf-8')
                                data_uri = f"data:{content_type};base64,{img_base64}"
                                self.image_cache[absolute_url] = data_uri
                                self.image_cache[original_url] = data_uri
                                print(f"배경 이미지 변환 완료: {original_url}")
                        except:
                            continue

                # 5. CSS 파일 내용의 모든 url() 변환
                if css_list:
                    print("CSS 파일 내의 이미지 URL 변환 시작...")
                    css_conversion_count = 0
                    import re
                    from urllib.parse import urljoin
                    

                    
                    for css_item in css_list:
                        css_content = css_item.get('content', '')
                        css_url = css_item.get('url', 'inline')
                        if not css_content:
                            continue
                        
                        # CSS 내의 모든 url() 패턴 찾기
                        url_pattern = r'url\s*\(\s*["\']?([^"\'()]+)["\']?\s*\)'
                        urls = re.findall(url_pattern, css_content, re.IGNORECASE)
                        
                        for url in urls:
                            # data: URL은 건너뛰기
                            if url.startswith('data:') or url.startswith('#'):
                                continue
                            
                            # 절대 URL 만들기
                            if url.startswith('http'):
                                absolute_url = url
                            elif css_url != 'inline' and css_url.startswith('http'):
                                absolute_url = urljoin(css_url, url)
                            else:
                                absolute_url = urljoin(current_url, url)
                            
                            # 이미 처리된 URL인지 체크 (중복 방지)
                            if absolute_url in self.session_processed_urls:
                                print(f"배경 이미지 중복 건너뛰기: {url}")
                                continue
                            
                            self.session_processed_urls.add(absolute_url)
                            
                            # 캐시에서 먼저 찾기
                            data_uri = self.image_cache.get(absolute_url) or self.image_cache.get(url)
                            
                            if not data_uri:
                                # 캐시에 없으면 새로 다운로드
                                try:
                                    # 이미지 파일인지 확인 (확장자 또는 content-type으로)
                                    is_image_by_extension = any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'])
                                    
                                    if is_image_by_extension:
                                        response = requests.get(absolute_url, timeout=5)
                                        if response.status_code == 200:
                                            content_type = response.headers.get('content-type', 'image/jpeg')
                                            if content_type.startswith('image/'):
                                                img_base64 = base64.b64encode(response.content).decode('utf-8')
                                                data_uri = f"data:{content_type};base64,{img_base64}"
                                                self.image_cache[absolute_url] = data_uri
                                                self.image_cache[url] = data_uri
                                    else:
                                        # 확장자가 없어도 시도해보고 content-type으로 판단
                                        try:
                                            response = requests.get(absolute_url, timeout=5)
                                            if response.status_code == 200:
                                                content_type = response.headers.get('content-type', '')
                                                if content_type.startswith('image/'):
                                                    img_base64 = base64.b64encode(response.content).decode('utf-8')
                                                    data_uri = f"data:{content_type};base64,{img_base64}"
                                                    self.image_cache[absolute_url] = data_uri
                                                    self.image_cache[url] = data_uri
                                                    print(f"확장자 없는 이미지 발견: {url} -> {content_type}")
                                        except Exception as no_ext_error:
                                            print(f"확장자 없는 파일 확인 실패: {url} - {str(no_ext_error)}")
                                            pass
                                except Exception as css_error:
                                    print(f"CSS 이미지 다운로드 실패: {url} - {str(css_error)}")
                                    continue
                            
                            # CSS 내용에서 URL 교체
                            if data_uri:
                                # 다양한 패턴으로 교체
                                replacement_patterns = [
                                    (f'url("{url}")', f'url("{data_uri}")'),
                                    (f"url('{url}')", f"url('{data_uri}')"),
                                    (f'url({url})', f'url("{data_uri}")'),
                                    # 공백이 있는 경우
                                    (f'url( "{url}" )', f'url("{data_uri}")'),
                                    (f"url( '{url}' )", f"url('{data_uri}')"),
                                    (f'url( {url} )', f'url("{data_uri}")'),
                                ]
                                
                                for old_pattern, new_pattern in replacement_patterns:
                                    if old_pattern in css_content:
                                        css_content = css_content.replace(old_pattern, new_pattern)
                                        print(f"CSS 내 이미지 변환 (패턴): {old_pattern}")
                                
                                # 정규식으로 더 복잡한 패턴 처리
                                import re
                                regex_pattern = rf'url\s*\(\s*["\']?\s*{re.escape(url)}\s*["\']?\s*\)'
                                if re.search(regex_pattern, css_content, re.IGNORECASE):
                                    css_content = re.sub(regex_pattern, f'url("{data_uri}")', css_content, flags=re.IGNORECASE)
                                    print(f"CSS 내 이미지 변환 (정규식): {url}")
                                
                                css_conversion_count += 1
                        
                        # 변환된 CSS 내용 업데이트
                        css_item['content'] = css_content
                    
                    print(f"CSS 내 이미지 {css_conversion_count}개 추가 변환 완료")
                
                # shared_dict 업데이트 (기존 구조 유지, 필드별 업데이트)
                css_json_string = json.dumps(css_list, ensure_ascii=False)
                shared_dict['SYSTEM_SELENIUM']['html'] = page_source
                shared_dict['SYSTEM_SELENIUM']['css'] = css_json_string
                shared_dict['SYSTEM_SELENIUM']['url'] = current_url
                # driver는 기존 것 유지 (덮어쓰지 않음)
                
                # HTML 변환 상태 업데이트
                if should_convert_images and img_result:
                    # 이미지 변환을 실행했으면 상태 업데이트
                    self.html_conversion_init = True
                    self.last_html_content = page_source
                    print("✅ 이미지 변환 완료 - 다음부터는 최적화 모드")
                elif not should_convert_images:
                    # 이미지 변환을 건너뛴 경우에도 HTML 내용 업데이트
                    self.last_html_content = page_source
                    print("⚡ 최적화 모드 - 이미지 변환 건너뜀")
                
                # 스크롤 동기화 (iframe에서 받은 좌표로 Selenium 스크롤)
                print(f"🔍 스크롤 동기화 시도: ({scroll_x}, {scroll_y})")
                scroll_synced = False
                try:
                    driver.execute_script(f"window.scrollTo({scroll_x}, {scroll_y});")
                    print(f"📜 Selenium 스크롤 동기화 완료: ({scroll_x}, {scroll_y})")
                    scroll_synced = True
                except Exception as scroll_error:
                    print(f"⚠️ 스크롤 동기화 실패: {str(scroll_error)}")
                    scroll_synced = False
                
                # 스크롤 동기화 여부 확인
                
                print("HTML 뷰어 새로고침 성공 (데이터 변환)")
                
                return {
                    'success': True,
                    'message': 'SYSTEM_SELENIUM 데이터가 새로고침되었습니다',
                    'html_length': len(page_source),
                    'css_count': len(css_list),
                    'url': current_url,
                    'scroll_synced': scroll_synced,
                    'scroll_position': {'x': scroll_x, 'y': scroll_y},
                    'image_conversion': {
                        'executed': should_convert_images,
                        'initialized': self.html_conversion_init,
                        'html_diff': html_length_diff
                    },
                    'cache_info': {
                        'total_cached_images': len(self.image_cache),
                        'images_processed': success_count if should_convert_images else 0
                    }
                }
                
        except Exception as e:
            error_msg = f"새로고침 실패: {str(e)}"
            print(error_msg)
            return {'success': False, 'error': error_msg}
    
    def reset_html_conversion_init(self):
        """
        HTML 변환 초기화 변수를 False로 리셋하여 다음 refresh 시 강제로 이미지 재변환하도록 함
        """
        try:
            with self.lock:
                old_value = self.html_conversion_init
                self.html_conversion_init = False
                self.last_html_content = ""  # HTML 내용도 초기화
                self.image_cache.clear()  # 이미지 캐시도 초기화
                
                print(f"🔄 HTML 변환 초기화 리셋 완료")
                print(f"  - html_conversion_init: {old_value} → {self.html_conversion_init}")
                print(f"  - 이미지 캐시 초기화됨")
                
                return {
                    'success': True, 
                    'message': 'HTML 변환 초기화가 리셋되었습니다. 다음 refresh 시 이미지를 재변환합니다.',
                    'old_value': old_value,
                    'new_value': self.html_conversion_init,
                    'cache_cleared': True
                }
                
        except Exception as e:
            error_msg = f"HTML 변환 초기화 리셋 실패: {str(e)}"
            print(error_msg)
            return {'success': False, 'error': error_msg}
    
    def get_history(self) -> List[str]:
        """실행 기록을 가져옵니다."""
        with self.lock:
            return self.history.copy()
    
    def get_remaining_time(self) -> int:
        """남은 시간을 초 단위로 반환합니다."""
        remaining = self.expiry_time - datetime.now()
        return max(0, int(remaining.total_seconds()))
    
    def extend_timeout(self, additional_hours: int = 12):
        """시간제한을 연장합니다."""
        with self.lock:
            self.timeout_hours += additional_hours
            self.expiry_time = self.expiry_time + timedelta(hours=additional_hours)
    
    def shutdown(self):
        """커널을 종료합니다."""
        with self.lock:
            self.is_shutdown = True
            self.namespace.clear()
            self.history.clear()
            self.file_user_info.clear() # 커널 종료 시 파일 정보도 초기화
    
    def set_file_user_info(self, file_path: str, user_id: str):
        """커널에 파일 경로와 사용자 ID 정보를 저장합니다."""
        with self.lock:
            # 기존 정보가 있으면 제거하고 새로운 정보로 교체
            self.file_user_info.clear()
            self.file_user_info[(file_path, user_id)] = True

    
    def get_file_user_info(self) -> Optional[Tuple[str, str]]:
        """커널에 저장된 파일 경로와 사용자 ID 정보를 반환합니다."""
        with self.lock:
            if self.file_user_info:
                # 딕셔너리의 첫 번째 키-값 쌍을 가져오기
                for key, value in self.file_user_info.items():
                    # 해당 항목 제거
                    del self.file_user_info[key]
                    return key  # (file_path, user_id) 튜플 반환
            return None
    



class ProcessKernel:
    """
    프로세스 기반 커널 클래스
    실제 실행 중인 Python 프로세스를 관리합니다.
    """
    
    def __init__(self, kernel_id: str, pid: int, proc_info: Dict[str, Any]):
        self.kernel_id = kernel_id
        self.pid = pid
        self.proc_info = proc_info
        self.namespace = {'shared_dict': {}}  # shared_dict 초기화
        self.history = []
        self.lock = threading.Lock()
        self.is_shutdown = False
        self.file_user_info = {} # 파일 경로와 사용자 ID 정보를 저장할 딕셔너리
    
    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """프로세스에서 코드를 실행합니다."""
        if self.is_shutdown:
            raise RuntimeError("커널이 종료되었습니다.")
        
        try:
            import io
            import sys
            import contextlib
            
            print(f"=== 프로세스 커널 실행 시작: {self.kernel_id} ===")
            print(f"실행할 코드: {code}")
            
            # 출력 캡처를 위한 StringIO 객체들
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # 실행 시작 시간
            start_time = datetime.now()
            
            print(f"=== 프로세스 커널 실행 시작: {self.kernel_id} ===")
            print(f"실행할 코드: {code}")
            
            # stdout과 stderr를 캡처하면서 코드 실행
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                try:
                    # 코드 컴파일
                    compiled_code = compile(code, '<string>', 'exec')
                    
                    # 실행 전 네임스페이스 백업 (오류 발생 시 복구용)
                    namespace_backup = self.namespace.copy()
                    
                    # 코드 실행
                    exec(compiled_code, self.namespace)
                    
                except SyntaxError as e:
                    # 구문 오류 처리
                    raise SyntaxError(f"구문 오류: {str(e)}")
                except NameError as e:
                    # 이름 오류 처리 (변수/함수 미정의)
                    raise NameError(f"이름 오류: {str(e)}")
                except TypeError as e:
                    # 타입 오류 처리
                    raise TypeError(f"타입 오류: {str(e)}")
                except ValueError as e:
                    # 값 오류 처리
                    raise ValueError(f"값 오류: {str(e)}")
                except Exception as e:
                    # 기타 모든 오류 처리
                    # 네임스페이스 복구 시도
                    try:
                        self.namespace = namespace_backup
                    except:
                        pass
                    raise e
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 캡처된 출력 가져오기
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            print(f"stdout 캡처: {repr(stdout_output)}")
            print(f"stderr 캡처: {repr(stderr_output)}")
            
            # 실행 기록에 추가
            self.history.append({
                'code': code,
                'stdout': stdout_output,
                'stderr': stderr_output,
                'execution_time': execution_time,
                'timestamp': datetime.now()
            })
            
            result = {
                'success': True,
                'stdout': stdout_output,
                'stderr': stderr_output,
                'execution_time': execution_time,
                'execution_count': len(self.history)
            }
            
            print(f"=== 프로세스 커널 실행 완료: {self.kernel_id} ===")
            print(f"결과: {result}")
            
            return result
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            
            print(f"=== 프로세스 커널 실행 오류: {self.kernel_id} ===")
            print(f"오류: {str(e)}")
            print(f"트레이스백: {error_traceback}")
            
            # 오류 발생 시에도 실행 기록에 추가
            self.history.append({
                'code': code,
                'stdout': '',
                'stderr': error_traceback,
                'execution_time': 0.0,
                'timestamp': datetime.now(),
                'error': str(e)
            })
            
            result = {
                'success': False,
                'stdout': '',
                'stderr': error_traceback,
                'error': str(e),
                'execution_time': 0.0,
                'execution_count': len(self.history)
            }
            
            print(f"=== 프로세스 커널 실행 오류 완료: {self.kernel_id} ===")
            print(f"커널 상태: 정상 유지 (오류 발생해도 커널은 계속 실행됨)")
            
            return result
    
    def get_namespace(self) -> Dict[str, Any]:
        """네임스페이스를 가져옵니다."""
        with self.lock:
            return self.namespace.copy()
    
    def clear_namespace(self):
        """네임스페이스를 초기화합니다."""
        with self.lock:
            # shared_dict는 유지하고 나머지만 초기화
            shared_dict = self.namespace.get('shared_dict', {})
            self.namespace.clear()
            self.namespace['shared_dict'] = shared_dict
            self.history.clear()
    
    def get_history(self) -> List[str]:
        """실행 기록을 가져옵니다."""
        with self.lock:
            return self.history.copy()
    
    def get_remaining_time(self) -> int:
        """남은 시간을 초 단위로 반환합니다."""
        # 프로세스 기반 커널은 프로세스가 종료될 때까지 시간이 남아있으므로 0을 반환
        return 0
    
    def extend_timeout(self, additional_hours: int = 12):
        """시간제한을 연장합니다."""
        # 프로세스 기반 커널은 프로세스가 종료될 때까지 시간이 남아있으므로 아무 작업도 하지 않음
        pass
    
    def shutdown(self):
        """커널을 종료합니다."""
        with self.lock:
            self.is_shutdown = True
            self.namespace.clear()
            self.history.clear()
            self.file_user_info.clear() # 커널 종료 시 파일 정보도 초기화
    
    def set_file_user_info(self, file_path: str, user_id: str):
        """커널에 파일 경로와 사용자 ID 정보를 저장합니다."""
        print(f"=== ProcessKernel.set_file_user_info 시작: {file_path}, {user_id} ===")
        with self.lock:
            # 기존 정보가 있으면 제거하고 새로운 정보로 교체
            print(f"기존 file_user_info: {self.file_user_info}")
            self.file_user_info.clear()
            print(f"file_user_info 초기화 완료")
            self.file_user_info[(file_path, user_id)] = True
            print(f"새로운 정보 저장: {(file_path, user_id)} -> True")
            print(f"최종 file_user_info: {self.file_user_info}")
        print(f"=== ProcessKernel.set_file_user_info 완료 ===")
    
    def get_file_user_info(self) -> Optional[Tuple[str, str]]:
        """커널에 저장된 파일 경로와 사용자 ID 정보를 반환합니다."""
        with self.lock:
            if self.file_user_info:
                # 딕셔너리의 첫 번째 키-값 쌍을 가져오기
                for key, value in self.file_user_info.items():
                    # 해당 항목 제거
                    del self.file_user_info[key]
                    return key  # (file_path, user_id) 튜플 반환
            return None


# 전역 커널 매니저 인스턴스
kernel_manager = KernelManager()


def create_kernel(kernel_id: Optional[str] = None) -> str:
    """새로운 커널을 생성합니다."""
    return kernel_manager.create_kernel(kernel_id)


def delete_kernel(kernel_id: str) -> bool:
    """커널을 삭제합니다."""
    return kernel_manager.delete_kernel(kernel_id)


def execute_code(kernel_id: str, code: str, timeout: float = 30.0) -> Dict[str, Any]:
    """커널에서 코드를 실행합니다."""
    return kernel_manager.execute_code(kernel_id, code, timeout)


def get_kernel(kernel_id: str) -> Optional['Kernel']:
    """커널을 가져옵니다."""
    return kernel_manager.get_kernel(kernel_id)

def get_kernel_status(kernel_id: str) -> Dict[str, Any]:
    """커널 상태를 반환합니다."""
    return kernel_manager.get_kernel_status(kernel_id)


def list_kernels() -> List[str]:
    """모든 커널 ID 목록을 반환합니다."""
    return kernel_manager.list_kernels()


def shutdown_all_kernels():
    """모든 커널을 종료합니다."""
    kernel_manager.shutdown_all()

def set_file_kernel_mapping(file_path: str, kernel_id: str):
    """파일과 커널의 매핑을 설정합니다."""
    kernel_manager.set_file_kernel_mapping(file_path, kernel_id)

def get_file_kernel_mapping(file_path: str) -> Optional[str]:
    """파일의 커널 ID를 반환합니다."""
    return kernel_manager.get_file_kernel_mapping(file_path)

def remove_file_kernel_mapping(file_path: str):
    """파일과 커널의 매핑을 제거합니다."""
    kernel_manager.remove_file_kernel_mapping(file_path)

def get_all_file_kernel_mappings() -> Dict[str, str]:
    """모든 파일-커널 매핑을 반환합니다."""
    return kernel_manager.get_all_file_kernel_mappings()

def get_all_file_user_kernel_mappings() -> Dict[Tuple[str, str], str]:
    """모든 파일-사용자-커널 매핑을 반환합니다."""
    return kernel_manager.get_all_file_user_kernel_mappings()

def set_file_user_kernel_mapping(file_path: str, user_id: str, kernel_id: str):
    """파일 경로와 사용자 ID에 대한 커널 매핑을 설정합니다."""
    kernel_manager.set_file_user_kernel_mapping(file_path, user_id, kernel_id)

def get_file_user_kernel_mapping(file_path: str, user_id: str) -> Optional[str]:
    """파일 경로와 사용자 ID에 대한 커널 ID를 가져옵니다."""
    return kernel_manager.get_file_user_kernel_mapping(file_path, user_id)

def remove_file_user_kernel_mapping(file_path: str, user_id: str) -> Optional[str]:
    """파일 경로와 사용자 ID에 대한 커널 매핑을 제거합니다."""
    return kernel_manager.remove_file_user_kernel_mapping(file_path, user_id)

def restore_file_user_mappings() -> Dict[Tuple[str, str], str]:
    """기존 커널들에서 파일 경로와 사용자 ID 정보를 복원합니다."""
    return kernel_manager.restore_file_user_mappings()

def get_kernel_remaining_time(kernel_id: str) -> Dict[str, Any]:
    """커널의 남은 시간을 반환합니다."""
    kernel = kernel_manager.get_kernel(kernel_id)
    if kernel is None:
        return {'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'}
    
    remaining_seconds = kernel.get_remaining_time()
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60
    
    return {
        'success': True,
        'remaining_seconds': remaining_seconds,
        'remaining_hours': hours,
        'remaining_minutes': minutes,
        'remaining_seconds_only': seconds,
        'expired': remaining_seconds <= 0
    }

def extend_kernel_timeout(kernel_id: str, additional_hours: int = 12) -> Dict[str, Any]:
    """커널 시간제한을 연장합니다."""
    kernel = kernel_manager.get_kernel(kernel_id)
    if kernel is None:
        return {'error': f'커널을 찾을 수 없습니다: {kernel_id}'}
    
    kernel.extend_timeout(additional_hours)
    return {
        'success': True,
        'message': f'커널 {kernel_id} 시간제한이 {additional_hours}시간 연장되었습니다',
        'new_expiry_time': kernel.expiry_time.isoformat()
    }


def scan_process_kernels():
    """실행 중인 Python 프로세스들을 스캔하여 커널로 인식합니다."""
    return kernel_manager.scan_process_kernels()


def get_process_kernel_status(kernel_id: str) -> Dict[str, Any]:
    """프로세스 커널의 상태를 반환합니다."""
    return kernel_manager.get_process_kernel_status(kernel_id)


def terminate_process_kernel(kernel_id: str) -> bool:
    """프로세스 커널을 종료합니다."""
    return kernel_manager.terminate_process_kernel(kernel_id)


# 사용 예시
if __name__ == "__main__":
    # 커널 생성
    kernel_id = create_kernel("test_kernel")
    print(f"커널 생성: {kernel_id}")
    
    # 코드 실행
    result = execute_code(kernel_id, "print('Hello, World!')")
    print(f"실행 결과: {result}")
    
    # 변수 설정 및 사용
    result = execute_code(kernel_id, "x = 10\ny = 20\nprint(f'x + y = {x + y}')")
    print(f"실행 결과: {result}")
    
    # 커널 상태 확인
    status = get_kernel_status(kernel_id)
    print(f"커널 상태: {status}")
    
    # 커널 삭제
    delete_kernel(kernel_id)
    print("커널 삭제 완료") 