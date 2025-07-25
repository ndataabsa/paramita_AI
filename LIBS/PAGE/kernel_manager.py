"""
커널 관리 관련 함수들
"""
import json
import hashlib
from flask import jsonify, request, session
from CLASS import CLASS_kernel_manager

# 파일 경로와 사용자 ID 기반 커널 매핑 저장소
file_user_kernel_mappings = {}  # {(file_path, user_id): kernel_id}

def generate_kernel_id(file_path, user_id):
    """파일 경로와 사용자 ID를 기반으로 커널 ID를 생성합니다."""
    # 파일 경로와 사용자 ID를 조합하여 고유한 문자열 생성
    combined = f"{file_path}_{user_id}"
    # SHA-256 해시를 사용하여 커널 ID 생성
    hash_object = hashlib.sha256(combined.encode())
    kernel_id = f"kernel_{hash_object.hexdigest()[:8]}"
    return kernel_id

def get_file_user_kernel_id(file_path, user_id):
    """파일 경로와 사용자 ID에 해당하는 커널 ID를 반환하거나 새로 생성합니다."""
    # 먼저 기존 매핑에서 찾기
    existing_kernel_id = CLASS_kernel_manager.get_file_user_kernel_mapping(file_path, user_id)
    if existing_kernel_id:
        return existing_kernel_id
    
    # 기존 커널 ID 생성
    kernel_id = generate_kernel_id(file_path, user_id)
    
    # 기존 커널이 존재하는지 확인
    existing_kernel = CLASS_kernel_manager.get_kernel(kernel_id)
    if existing_kernel:
        # 매핑 설정
        CLASS_kernel_manager.set_file_user_kernel_mapping(file_path, user_id, kernel_id)
        return kernel_id
    else:
        # 새 커널 생성
        try:
            CLASS_kernel_manager.create_kernel(kernel_id)
            
            # 매핑 설정
            CLASS_kernel_manager.set_file_user_kernel_mapping(file_path, user_id, kernel_id)
            
            return kernel_id
        except Exception as e:
            print(f"커널 생성 실패: {str(e)}")
            return None

def restore_existing_kernels():
    """새로고침 후 기존 커널들을 복원합니다."""
    try:
        # 모든 커널 목록 가져오기
        all_kernels = CLASS_kernel_manager.list_kernels()
        
        # 커널 매니저에서 파일-사용자 매핑 복원
        restored_mappings = CLASS_kernel_manager.restore_file_user_mappings()
        
    except Exception as e:
        print(f"기존 커널 복원 중 오류: {str(e)}")

def get_file_user_kernel(file_path, user_id):
    """파일 경로와 사용자 ID에 해당하는 커널 객체를 반환합니다."""
    try:
        kernel_id = get_file_user_kernel_id(file_path, user_id)
        if kernel_id is None:
            print(f"파일 {file_path}, 사용자 {user_id}의 커널 ID를 가져올 수 없습니다.")
            return None
            
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        return kernel
    except Exception as e:
        print(f"파일 {file_path}, 사용자 {user_id}의 커널 가져오기 오류: {str(e)}")
        return None

def refresh_selenium_data_with_conversion(kernel_id, scroll_x=0, scroll_y=0):
    """
    HTML 뷰어용: SYSTEM_SELENIUM 데이터를 새로고침하고 CSS/이미지를 data URI로 변환
    jupyapp.py의 복잡한 로직을 여기로 이동했습니다.
    """
    try:
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        if not kernel:
            return {'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'}
        
        # kernel 클래스의 새로고침 메서드 호출 (JS 코드는 kernel 내부에 있음)
        result = kernel.refresh_selenium_with_data_conversion(scroll_x, scroll_y)
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': f'새로고침 중 오류: {str(e)}'}


def reset_html_conversion_init(kernel_id):
    """
    HTML 뷰어용: HTML 변환 초기화 변수를 False로 리셋
    다음 refresh 시 강제로 이미지 재변환하도록 함
    """
    try:
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        if not kernel:
            return {'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'}
        
        # kernel 클래스의 init 리셋 메서드 호출
        result = kernel.reset_html_conversion_init()
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': f'HTML 변환 초기화 리셋 중 오류: {str(e)}'}

def get_file_user_kernel_namespace(file_path, user_id):
    """파일 경로와 사용자 ID에 해당하는 커널의 네임스페이스를 반환합니다."""
    try:
        kernel = get_file_user_kernel(file_path, user_id)
        if kernel is None:
            return jsonify({'success': False, 'error': f'파일 {file_path}, 사용자 {user_id}의 커널을 찾을 수 없습니다'})
        
        namespace = kernel.get_namespace()
        
        # JSON 직렬화 가능한 형태로 변환
        serializable_namespace = {}
        for key, value in namespace.items():
            try:
                # 기본 타입들은 그대로 사용
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    serializable_namespace[key] = value
                else:
                    # 다른 타입들은 문자열로 변환
                    serializable_namespace[key] = str(value)
            except Exception:
                # 변환 실패시 문자열로 변환
                serializable_namespace[key] = str(value)
        
        return jsonify({
            'success': True,
            'namespace': serializable_namespace
        })
    except Exception as e:
        import traceback
        print(f"파일 {file_path}, 사용자 {user_id}의 커널 네임스페이스 가져오기 오류: {str(e)}")
        print(f"트레이스백: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})

def execute_file_user_kernel_code(file_path, user_id):
    """파일 경로와 사용자 ID에 해당하는 커널에서 코드를 실행합니다."""
    try:
        data = request.get_json()
        code = data.get('code', '')
        timeout = data.get('timeout', 30.0)
        
        if not code.strip():
            return jsonify({'success': False, 'error': '실행할 코드가 필요합니다'})
        
        kernel_id = get_file_user_kernel_id(file_path, user_id)
        result = CLASS_kernel_manager.execute_code(kernel_id, code, timeout)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def clear_file_user_kernel_namespace(file_path, user_id):
    """파일 경로와 사용자 ID에 해당하는 커널 네임스페이스를 초기화합니다."""
    try:
        kernel = get_file_user_kernel(file_path, user_id)
        if kernel is None:
            return jsonify({'success': False, 'error': f'파일 {file_path}, 사용자 {user_id}의 커널을 찾을 수 없습니다'})
        
        kernel.clear_namespace()
        
        return jsonify({
            'success': True,
            'message': f'파일 {file_path}, 사용자 {user_id}의 커널 네임스페이스가 초기화되었습니다'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def get_kernels():
    """모든 커널 목록을 반환합니다."""
    try:
        kernels = CLASS_kernel_manager.list_kernels()
        
        # 모든 파일-사용자 매핑도 출력
        all_mappings = CLASS_kernel_manager.get_all_file_user_kernel_mappings()
        
        kernel_statuses = {}
        for kernel_id in kernels:
            status = CLASS_kernel_manager.get_kernel_status(kernel_id)
            kernel_statuses[kernel_id] = status
        
        result = {
            'success': True,
            'kernels': kernel_statuses
        }
        return jsonify(result)
    except Exception as e:
        print(f"커널 목록 가져오기 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def create_file_user_kernel():
    """파일과 사용자 정보를 포함하여 커널을 생성합니다."""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        user_id = session.get('user_id')
        
        if not file_path:
            return jsonify({'success': False, 'error': 'file_path가 필요합니다'})
        
        if not user_id:
            return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
        
        # 파일-사용자 커널 ID 생성 또는 가져오기
        kernel_id = get_file_user_kernel_id(file_path, user_id)
        
        if kernel_id:
            return jsonify({
                'success': True,
                'kernel_id': kernel_id,
                'message': f'커널이 생성되었습니다: {kernel_id}'
            })
        else:
            return jsonify({'success': False, 'error': '커널 생성에 실패했습니다'})
            
    except Exception as e:
        print(f"파일-사용자 커널 생성 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def create_new_kernel():
    """새로운 커널을 생성합니다."""
    try:
        data = request.get_json()
        kernel_id = data.get('kernel_id') if data else None
        
        # kernel_id가 None이면 자동으로 생성
        if kernel_id is None:
            import uuid
            kernel_id = f"kernel_{uuid.uuid4().hex[:8]}"
        
        new_kernel_id = CLASS_kernel_manager.create_kernel(kernel_id)
        
        return jsonify({
            'success': True,
            'kernel_id': new_kernel_id,
            'message': f'커널이 생성되었습니다: {new_kernel_id}'
        })
    except Exception as e:
        print(f"커널 생성 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def delete_kernel_api(kernel_id):
    """커널을 삭제합니다."""
    try:
        # 먼저 해당 커널과 연결된 파일-사용자 매핑 삭제
        user_id = session.get('user_id')
        if user_id:
            all_mappings = CLASS_kernel_manager.get_all_file_user_kernel_mappings()
            if all_mappings:
                for (file_path, mapping_user_id), mapping_kernel_id in list(all_mappings.items()):
                    if mapping_kernel_id == kernel_id and mapping_user_id == user_id:
                        CLASS_kernel_manager.remove_file_user_kernel_mapping(file_path, user_id)
                
        
        # 커널 삭제
        success = CLASS_kernel_manager.delete_kernel(kernel_id)
        if success:
            return jsonify({
                'success': True,
                'message': f'커널이 삭제되었습니다: {kernel_id}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'커널을 찾을 수 없습니다: {kernel_id}'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def get_kernel_status_api(kernel_id):
    """커널 상태를 반환합니다."""
    try:
        status = CLASS_kernel_manager.get_kernel_status(kernel_id)
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def execute_kernel_code(kernel_id):
    """커널에서 코드를 실행합니다."""
    try:
        data = request.get_json()
        code = data.get('code', '')
        timeout = data.get('timeout', 30.0)
        
        if not code.strip():
            return jsonify({'success': False, 'error': '실행할 코드가 필요합니다'})
        
        result = CLASS_kernel_manager.execute_code(kernel_id, code, timeout)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def get_kernel_history(kernel_id):
    """커널 실행 기록을 반환합니다."""
    try:
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        
        if kernel is None:
            return jsonify({'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'})
        
        limit = request.args.get('limit', type=int)
        history = kernel.get_history(limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def get_kernel_namespace(kernel_id):
    """커널 네임스페이스를 반환합니다."""
    try:
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        
        if kernel is None:
            return jsonify({'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'})
        
        namespace = kernel.get_namespace()
        
        # JSON 직렬화 가능한 형태로 변환
        serializable_namespace = {}
        for key, value in namespace.items():
            try:
                # 기본 타입들은 그대로 사용
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    serializable_namespace[key] = value
                else:
                    # 다른 타입들은 문자열로 변환
                    serializable_namespace[key] = str(value)
            except Exception:
                # 변환 실패시 문자열로 변환
                serializable_namespace[key] = str(value)
        
        return jsonify({
            'success': True,
            'namespace': serializable_namespace
        })
    except Exception as e:
        import traceback
        print(f"커널 {kernel_id} 네임스페이스 가져오기 오류: {str(e)}")
        print(f"트레이스백: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})


def get_shared_dict(kernel_id):
    """커널의 shared_dict만 딕셔너리 형태로 반환합니다."""
    try:
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        
        if kernel is None:
            return jsonify({'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'})
        
        namespace = kernel.get_namespace()
        
        # shared_dict 키만 가져오기
        if 'shared_dict' not in namespace:
            return jsonify({
                'success': True,
                'shared_dict': {}
            })
        
        shared_dict_value = namespace['shared_dict']
        
        # shared_dict가 딕셔너리가 아닌 경우 빈 딕셔너리 반환
        if not isinstance(shared_dict_value, dict):
            return jsonify({
                'success': True,
                'shared_dict': {}
            })
        
        # shared_dict를 딕셔너리 형태로 변환
        shared_dict = {}
        for key, value in shared_dict_value.items():
            try:
                # 기본 타입들은 그대로 사용
                if isinstance(value, (str, int, float, bool, type(None))):
                    shared_dict[key] = value
                elif isinstance(value, (list, tuple)):
                    # 리스트와 튜플은 재귀적으로 처리
                    shared_dict[key] = []
                    for item in value:
                        if isinstance(item, (str, int, float, bool, type(None))):
                            shared_dict[key].append(item)
                        else:
                            shared_dict[key].append(str(item))
                elif isinstance(value, dict):
                    # 딕셔너리도 재귀적으로 처리
                    shared_dict[key] = {}
                    for k, v in value.items():
                        if isinstance(v, (str, int, float, bool, type(None))):
                            shared_dict[key][str(k)] = v
                        else:
                            shared_dict[key][str(k)] = str(v)
                else:
                    # 그 외 모든 타입은 문자열로 변환
                    shared_dict[key] = str(value)
            except Exception as e:
                # 변환 실패시 키와 함께 오류 정보를 문자열로 저장
                shared_dict[key] = f"<직렬화 불가능한 객체: {type(value).__name__}>"
        
        return jsonify({
            'success': True,
            'shared_dict': shared_dict
        })
    except Exception as e:
        import traceback
        print(f"커널 {kernel_id} shared_dict 가져오기 오류: {str(e)}")
        print(f"트레이스백: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})


def clear_kernel_namespace(kernel_id):
    """커널 네임스페이스를 초기화합니다."""
    try:
        kernel = CLASS_kernel_manager.get_kernel(kernel_id)
        
        if kernel is None:
            return jsonify({'success': False, 'error': f'커널을 찾을 수 없습니다: {kernel_id}'})
        
        kernel.clear_namespace()
        
        return jsonify({
            'success': True,
            'message': f'커널 네임스페이스가 초기화되었습니다: {kernel_id}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# 세션별 커널 관리 함수들 (파일 경로와 사용자 ID 기반으로 수정)
def get_session_kernel_id():
    """현재 세션의 커널 ID를 반환하거나 새로 생성합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
    
    # 현재 활성 파일 경로를 가져옴 (request에서 또는 세션에서)
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return jsonify({'success': False, 'error': '파일 경로가 없습니다'})
    
    return get_file_user_kernel_id(file_path, user_id)


def get_session_kernel():
    """현재 세션의 커널 객체를 반환합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return None
    
    return get_file_user_kernel(file_path, user_id)


def clear_session_kernel():
    """현재 세션의 커널을 초기화합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return None
    
    try:
        kernel = get_file_user_kernel(file_path, user_id)
        if kernel:
            kernel.clear_namespace()
            print(f"파일 {file_path}, 사용자 {user_id}의 커널 초기화")
        return get_file_user_kernel_id(file_path, user_id)
    except Exception as e:
        print(f"파일 {file_path}, 사용자 {user_id}의 커널 초기화 오류: {str(e)}")
        return None


def cleanup_session_kernel():
    """현재 세션의 커널을 정리합니다."""
    try:
        if 'kernel_id' in session:
            kernel_id = session['kernel_id']
            success = CLASS_kernel_manager.delete_kernel(kernel_id)
            if success:
                print(f"세션 커널 정리: {kernel_id}")
            del session['kernel_id']
    except Exception as e:
        print(f"세션 커널 정리 오류: {str(e)}")


# 세션별 커널 API 엔드포인트들
def get_session_kernel_status():
    """현재 세션의 커널 상태를 반환합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return jsonify({'success': False, 'error': '파일 경로가 없습니다'})
    
    try:
        kernel_id = get_file_user_kernel_id(file_path, user_id)
        status = CLASS_kernel_manager.get_kernel_status(kernel_id)
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        print(f"파일 {file_path}, 사용자 {user_id} 커널 상태 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def execute_session_kernel_code():
    """현재 세션의 커널에서 코드를 실행합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return jsonify({'success': False, 'error': '파일 경로가 없습니다'})
    
    return execute_file_user_kernel_code(file_path, user_id)


def get_session_kernel_namespace():
    """현재 세션의 커널 네임스페이스를 반환합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return jsonify({'success': False, 'error': '파일 경로가 없습니다'})
    
    return get_file_user_kernel_namespace(file_path, user_id)


def clear_session_kernel_namespace():
    """현재 세션의 커널 네임스페이스를 초기화합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return jsonify({'success': False, 'error': '파일 경로가 없습니다'})
    
    return clear_file_user_kernel_namespace(file_path, user_id)


def get_session_kernel_history():
    """현재 세션의 커널 실행 기록을 반환합니다."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '사용자 ID가 없습니다'})
    
    # 현재 활성 파일 경로를 가져옴
    file_path = request.args.get('file_path') or session.get('active_file')
    if not file_path:
        return jsonify({'success': False, 'error': '파일 경로가 없습니다'})
    
    try:
        kernel = get_file_user_kernel(file_path, user_id)
        if kernel is None:
            return jsonify({'success': False, 'error': f'파일 {file_path}, 사용자 {user_id}의 커널을 찾을 수 없습니다'})
        
        limit = request.args.get('limit', type=int)
        history = kernel.get_history(limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def cleanup_session_kernel_api():
    """현재 세션의 커널을 정리합니다."""
    try:
        cleanup_session_kernel()
        return jsonify({
            'success': True,
            'message': '세션 커널이 정리되었습니다'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# 파일-커널 매핑 관련 함수들
def set_file_kernel_mapping_api():
    """파일과 커널의 매핑을 설정합니다."""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        kernel_id = data.get('kernel_id')
        
        if not file_path or not kernel_id:
            return jsonify({
                'success': False,
                'error': 'file_path와 kernel_id가 필요합니다'
            })
        
        CLASS_kernel_manager.set_file_kernel_mapping(file_path, kernel_id)
        
        return jsonify({
            'success': True,
            'message': f'파일-커널 매핑이 설정되었습니다: {file_path} -> {kernel_id}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def get_file_kernel_mapping_api():
    """파일의 커널 ID를 반환합니다."""
    try:
        file_path = request.args.get('file_path')
        user_id = session.get('user_id')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path가 필요합니다'
            })
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': '사용자 ID가 없습니다'
            })
        
        # 사용자별 파일-커널 매핑 확인
        kernel_id = CLASS_kernel_manager.get_file_user_kernel_mapping(file_path, user_id)
        
        return jsonify({
            'success': True,
            'kernel_id': kernel_id
        })
    except Exception as e:
        print(f"get_file_kernel_mapping_api 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def remove_file_kernel_mapping_api():
    """파일과 커널의 매핑을 제거합니다."""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path가 필요합니다'
            })
        
        CLASS_kernel_manager.remove_file_kernel_mapping(file_path)
        
        return jsonify({
            'success': True,
            'message': f'파일-커널 매핑이 제거되었습니다: {file_path}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def get_all_file_kernel_mappings_api():
    """모든 파일-커널 매핑을 반환합니다."""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': '사용자 ID가 없습니다'
            })
        
        # 현재 사용자의 파일-사용자-커널 매핑만 가져오기
        user_mappings = CLASS_kernel_manager.get_all_file_user_kernel_mappings()
        current_user_mappings = {}
        
        if user_mappings:
            # 현재 사용자에 해당하는 매핑만 필터링
            for (file_path, mapping_user_id), kernel_id in user_mappings.items():
                if mapping_user_id == user_id:
                    current_user_mappings[file_path] = kernel_id
        
        return jsonify({
            'success': True,
            'mappings': current_user_mappings
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 커널 시간제한 관련 함수들
def get_kernel_remaining_time(kernel_id):
    """커널의 남은 시간을 반환합니다."""
    try:
        remaining_time = CLASS_kernel_manager.get_kernel_remaining_time(kernel_id)
        return jsonify({
            'success': True,
            'remaining_time': remaining_time
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def extend_kernel_timeout(kernel_id, additional_hours=12):
    """커널 시간제한을 연장합니다."""
    try:
        result = CLASS_kernel_manager.extend_kernel_timeout(kernel_id, additional_hours)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# 프로세스 커널 관련 함수들
def scan_process_kernels_api():
    """실행 중인 Python 프로세스들을 스캔하여 커널로 인식합니다."""
    try:

        CLASS_kernel_manager.scan_process_kernels()
        
        # 스캔 후 커널 목록 반환
        kernels = CLASS_kernel_manager.list_kernels()
        kernel_statuses = {}
        
        for kernel_id in kernels:
            status = CLASS_kernel_manager.get_kernel_status(kernel_id)
            kernel_statuses[kernel_id] = status
        
        return jsonify({
            'success': True,
            'message': '프로세스 커널 스캔이 완료되었습니다',
            'kernels': kernel_statuses
        })
    except Exception as e:
        print(f"프로세스 커널 스캔 API 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def get_process_kernel_status_api(kernel_id):
    """프로세스 커널의 상태를 반환합니다."""
    try:
        status = CLASS_kernel_manager.get_process_kernel_status(kernel_id)
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def terminate_process_kernel_api(kernel_id):
    """프로세스 커널을 종료합니다."""
    try:
        success = CLASS_kernel_manager.terminate_process_kernel(kernel_id)
        if success:
            return jsonify({
                'success': True,
                'message': f'프로세스 커널이 종료되었습니다: {kernel_id}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'프로세스 커널을 찾을 수 없거나 종료할 수 없습니다: {kernel_id}'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def add_process_kernel_to_project_api():
    """프로세스 커널을 프로젝트에 추가합니다."""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        kernel_id = data.get('kernel_id')
        user_id = session.get('user_id')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path가 필요합니다'
            })
        
        if not kernel_id:
            return jsonify({
                'success': False,
                'error': 'kernel_id가 필요합니다'
            })
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': '사용자 ID가 없습니다'
            })
        
        # 프로세스 커널인지 확인
        if not kernel_id.startswith('process_kernel_'):
            return jsonify({
                'success': False,
                'error': '프로세스 커널이 아닙니다'
            })
        
        # 파일-사용자-커널 매핑 설정
        CLASS_kernel_manager.set_file_user_kernel_mapping(file_path, user_id, kernel_id)
        
        return jsonify({
            'success': True,
            'message': f'프로세스 커널이 프로젝트에 추가되었습니다: {file_path} -> {kernel_id}'
        })
    except Exception as e:
        print(f"프로세스 커널 프로젝트 추가 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


def check_kernel_project_status_api(kernel_id):
    """커널이 현재 프로젝트에 속하는지 확인합니다."""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': '사용자 ID가 없습니다'
            })
        
        # 모든 파일-사용자-커널 매핑에서 해당 커널 찾기
        all_mappings = CLASS_kernel_manager.get_all_file_user_kernel_mappings()
        project_info = None
        
        if all_mappings:
            for (file_path, mapping_user_id), mapping_kernel_id in all_mappings.items():
                if mapping_kernel_id == kernel_id and mapping_user_id == user_id:
                    project_info = {
                        'file_path': file_path,
                        'file_name': file_path.split('/')[-1] if '/' in file_path else file_path,
                        'is_project_kernel': True
                    }
                    break
        
        if project_info:
            return jsonify({
                'success': True,
                'is_project_kernel': True,
                'project_info': project_info
            })
        else:
            return jsonify({
                'success': True,
                'is_project_kernel': False,
                'project_info': None
            })
            
    except Exception as e:
        print(f"커널 프로젝트 상태 확인 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def execute_session_kernel_code_direct(code: str) -> dict:
    """
    세션 커널에서 코드를 직접 실행 (AI 어시스턴트용)
    
    Args:
        code: 실행할 파이썬 코드
        
    Returns:
        실행 결과 딕셔너리
    """
    try:
        kernel = get_session_kernel()
        if kernel is None:
            return {'success': False, 'error': '세션 커널을 찾을 수 없습니다'}
        
        # 코드 실행
        result = kernel.execute_code(code)
        
        return {
            'success': True,
            'result': result,
            'output': result.get('output', ''),
            'error': result.get('error', ''),
            'execution_count': result.get('execution_count', 0)
        }
        
    except Exception as e:
        return {'success': False, 'error': f'코드 실행 중 오류: {str(e)}'}