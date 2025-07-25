"""
파일 브라우저 관련 API 함수들
"""
import os
import json
import glob
import base64
import shutil
from flask import jsonify, request, send_file
from werkzeug.utils import secure_filename
import configparser

# 설정 파일 읽기
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'setting.dat')
config = configparser.ConfigParser()
config.read_dict({'DEFAULT': {'root_dir': '.', 'users': ''}})
if os.path.exists(CONFIG_PATH):
    config.read(CONFIG_PATH)
ROOT_DIR = config['DEFAULT'].get('root_dir', '.')
ALLOWED_USERS = [u.strip() for u in config['DEFAULT'].get('users', '').split(',') if u.strip()]


def get_files():
    """설정된 루트 디렉토리의 파일 목록을 계층 구조로 반환합니다."""
    try:
        def build_tree_recursive(path=ROOT_DIR, depth=0, max_depth=2):
            """재귀적으로 디렉토리 트리를 구성합니다."""
            result = []
            if depth > max_depth:
                return result
            try:
                items = os.listdir(path)
            except PermissionError:
                return result
            items = [item for item in items if not item.startswith('.')]
            directories = []
            files = []
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    directories.append(item)
                else:
                    files.append(item)
            directories.sort(key=str.lower)
            files.sort(key=str.lower)
            for dir_name in directories:
                dir_path = os.path.join(path, dir_name)
                rel_path = os.path.relpath(dir_path, ROOT_DIR)
                children = build_tree_recursive(dir_path, depth+1, max_depth)
                result.append({
                    'name': dir_name,
                    'path': rel_path,
                    'type': 'directory',
                    'size': 0,
                    'children': children
                })
            for file_name in files:
                file_path = os.path.join(path, file_name)
                rel_path = os.path.relpath(file_path, ROOT_DIR)
                try:
                    file_size = os.path.getsize(file_path)
                    result.append({
                        'name': file_name,
                        'path': rel_path,
                        'type': 'file',
                        'size': file_size,
                        'children': []
                    })
                except (OSError, IOError):
                    continue
            return result
        
        # 트리 구조 구성
        file_tree = build_tree_recursive(ROOT_DIR)
        
        return jsonify({
            'success': True,
            'files': file_tree
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def get_file_content():
    """설정된 루트 디렉토리 기준으로 파일 내용을 반환합니다."""
    try:
        file_path = request.args.get('path', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': '파일 경로가 필요합니다'
            })
        
        # 경로 검증 (상위 디렉토리 접근 방지)
        if '..' in file_path or file_path.startswith('/'):
            return jsonify({
                'success': False,
                'error': '잘못된 파일 경로입니다'
            })
        
        full_path = os.path.join(ROOT_DIR, file_path)
        
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '파일을 찾을 수 없습니다'
            })
        
        if not os.path.isfile(full_path):
            return jsonify({
                'success': False,
                'error': '파일이 아닙니다'
            })
        
        # 파일 크기 제한 (10MB)
        file_size = os.path.getsize(full_path)
        if file_size > 10 * 1024 * 1024:
            return jsonify({
                'success': False,
                'error': '파일이 너무 큽니다 (10MB 제한)'
            })
        
        # 파일 확장자에 따른 처리
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            # 이미지 파일은 base64로 인코딩
            with open(full_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            file_type = 'image'
        else:
            # 텍스트 파일
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # UTF-8로 읽을 수 없는 경우 바이너리로 읽기
                with open(full_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
            file_type = 'text'
        
        return jsonify({
            'success': True,
            'content': content,
            'file_type': file_type,
            'file_size': file_size
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def save_file():
    """파일을 저장합니다."""
    try:
        data = request.get_json()
        file_path = data.get('path', '')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': '파일 경로가 필요합니다'
            })
        
        # 경로 검증
        if '..' in file_path or file_path.startswith('/'):
            return jsonify({
                'success': False,
                'error': '잘못된 파일 경로입니다'
            })
        
        full_path = os.path.join(ROOT_DIR, file_path)
        
        # 디렉토리 생성
        dir_path = os.path.dirname(full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            # 디렉토리에 sticky bit 설정 (새로 생성되는 파일들이 그룹 소유가 되도록)
            try:
                os.chmod(dir_path, 0o2775)  # drwxrwsr-x
            except Exception:
                pass  # 권한 설정 실패시 무시
        
        # 파일 저장
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 파일 생성 후 그룹 쓰기 권한 설정
        try:
            os.chmod(full_path, 0o664)  # rw-rw-r--
        except Exception:
            pass  # 권한 설정 실패시 무시
        
        return jsonify({
            'success': True,
            'message': '파일이 저장되었습니다'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def download_file():
    """파일을 다운로드합니다."""
    try:
        file_path = request.args.get('path', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': '파일 경로가 필요합니다'
            })
        
        # 경로 검증
        if '..' in file_path or file_path.startswith('/'):
            return jsonify({
                'success': False,
                'error': '잘못된 파일 경로입니다'
            })
        
        full_path = os.path.join(ROOT_DIR, file_path)
        
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '파일을 찾을 수 없습니다'
            })
        
        return send_file(full_path, as_attachment=True)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def delete_file():
    """파일을 삭제합니다."""
    try:
        data = request.get_json()
        file_path = data.get('path', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': '파일 경로가 필요합니다'
            })
        
        # 경로 검증
        if '..' in file_path or file_path.startswith('/'):
            return jsonify({
                'success': False,
                'error': '잘못된 파일 경로입니다'
            })
        
        full_path = os.path.join(ROOT_DIR, file_path)
        
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '파일을 찾을 수 없습니다'
            })
        
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        return jsonify({
            'success': True,
            'message': '파일이 삭제되었습니다'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def create_file():
    """새 파일을 생성합니다."""
    try:
        data = request.get_json()
        file_name = data.get('name', '')
        
        if not file_name:
            return jsonify({
                'success': False,
                'error': '파일 이름이 필요합니다'
            })
        
        # 파일명 검증
        if '..' in file_name or '/' in file_name or '\\' in file_name:
            return jsonify({
                'success': False,
                'error': '잘못된 파일 이름입니다'
            })
        
        full_path = os.path.join(ROOT_DIR, file_name)
        
        if os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '이미 존재하는 파일입니다'
            })
        
        # 빈 파일 생성
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write('')
        
        # 파일 생성 후 그룹 쓰기 권한 설정
        try:
            os.chmod(full_path, 0o664)  # rw-rw-r--
        except Exception:
            pass  # 권한 설정 실패시 무시
        
        return jsonify({
            'success': True,
            'message': '파일이 생성되었습니다'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def upload_file():
    """파일을 업로드합니다."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '파일이 없습니다'
            })
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '파일이 선택되지 않았습니다'
            })
        
        filename = secure_filename(file.filename)
        
        # 파일명 검증
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({
                'success': False,
                'error': '잘못된 파일 이름입니다'
            })
        
        full_path = os.path.join(ROOT_DIR, filename)
        
        if os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '이미 존재하는 파일입니다'
            })
        
        # 파일 저장
        file.save(full_path)
        
        # 파일 생성 후 그룹 쓰기 권한 설정
        try:
            os.chmod(full_path, 0o664)  # rw-rw-r--
        except Exception:
            pass  # 권한 설정 실패시 무시
        
        return jsonify({
            'success': True,
            'message': '파일이 업로드되었습니다'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def rename_file():
    """파일 이름을 변경합니다."""
    try:
        data = request.get_json()
        old_path = data.get('old_path', '')
        new_name = data.get('new_name', '')
        
        if not old_path or not new_name:
            return jsonify({
                'success': False,
                'error': '파일 경로와 새 이름이 필요합니다'
            })
        
        # 경로 검증
        if '..' in old_path or old_path.startswith('/') or '..' in new_name or '/' in new_name or '\\' in new_name:
            return jsonify({
                'success': False,
                'error': '잘못된 파일 경로 또는 이름입니다'
            })
        
        old_full_path = os.path.join(ROOT_DIR, old_path)
        new_full_path = os.path.join(ROOT_DIR, os.path.dirname(old_path), new_name)
        
        if not os.path.exists(old_full_path):
            return jsonify({
                'success': False,
                'error': '파일을 찾을 수 없습니다'
            })
        
        if os.path.exists(new_full_path):
            return jsonify({
                'success': False,
                'error': '이미 존재하는 파일입니다'
            })
        
        # 파일 이름 변경
        os.rename(old_full_path, new_full_path)
        
        return jsonify({
            'success': True,
            'message': '파일 이름이 변경되었습니다'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def get_file_browser_page_data(user_id=None):
    """파일 브라우저 페이지에 필요한 데이터를 반환합니다."""
    json_files = glob.glob(os.path.join(ROOT_DIR, '*.json'))
    selected_file = request.args.get('file', '')
    if selected_file and selected_file not in [os.path.basename(f) for f in json_files] and json_files:
        selected_file = os.path.basename(json_files[0])
    elif not selected_file and json_files:
        selected_file = os.path.basename(json_files[0])
    return {
        'json_files': [os.path.basename(f) for f in json_files],
        'selected_file': selected_file,
        'root_dir': ROOT_DIR,
        'allowed_users': ALLOWED_USERS,
        'user_id': user_id
    } 