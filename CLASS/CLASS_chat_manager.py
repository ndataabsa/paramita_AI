"""
채팅 매니저 클래스
여러 채팅 세션을 백그라운드에서 관리, 저장, 로드
"""

import os
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from MODULE.module_logger import log_message
from CLASS.class_chat import Chat
from MODULE.module_AI import get_ai_response, analyze_code_error

class ChatManager:
    def __init__(self, storage_path: str = "data/chats"):
        """
        채팅 매니저 초기화
        
        Args:
            storage_path: 채팅 데이터 저장 경로
        """
        self.storage_path = storage_path
        self.chats: Dict[str, Chat] = {}  # chat_id -> Chat 매핑
        self.user_chats: Dict[str, List[str]] = {}  # user_id -> chat_id 리스트
        self.active_chats: Dict[str, str] = {}  # user_id -> active_chat_id
        
        # 백그라운드 저장을 위한 스레드 락
        self._lock = threading.Lock()
        self._auto_save_enabled = True
        self._auto_save_interval = 30  # 30초마다 자동 저장
        
        # 초기화
        self._ensure_storage_directory()
        self._load_all_chats()
        self._start_auto_save_thread()
    
    def _ensure_storage_directory(self):
        """저장 디렉토리 생성"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
            log_message(f"채팅 저장 디렉토리 생성: {self.storage_path}")
    
    def _get_chat_file_path(self, chat_id: str) -> str:
        """채팅 파일 경로 반환"""
        return os.path.join(self.storage_path, f"{chat_id}.json")
    
    def _get_index_file_path(self) -> str:
        """인덱스 파일 경로 반환"""
        return os.path.join(self.storage_path, "chat_index.json")
    
    def create_chat(self, user_id: str, title: str = "새 채팅") -> Chat:
        """
        새 채팅 생성
        
        Args:
            user_id: 사용자 ID
            title: 채팅 제목
            
        Returns:
            생성된 Chat 인스턴스
        """
        with self._lock:
            chat = Chat(title=title, user_id=user_id)
            
            # 매니저에 등록
            self.chats[chat.id] = chat
            
            # 사용자 채팅 목록에 추가
            if user_id not in self.user_chats:
                self.user_chats[user_id] = []
            self.user_chats[user_id].append(chat.id)
            
            # 활성 채팅으로 설정
            self.active_chats[user_id] = chat.id
            chat.active = True
            
            # 즉시 저장
            self._save_chat(chat)
            self._save_index()
            
            log_message(f"새 채팅 생성: {chat.id} (사용자: {user_id})")
            return chat
    
    def get_chat(self, chat_id: str) -> Optional[Chat]:
        """채팅 ID로 채팅 가져오기"""
        return self.chats.get(chat_id)
    
    def get_user_chats(self, user_id: str) -> List[Chat]:
        """사용자의 모든 채팅 가져오기 (최신순)"""
        chat_ids = self.user_chats.get(user_id, [])
        chats = [self.chats[chat_id] for chat_id in chat_ids if chat_id in self.chats]
        
        # 최신 업데이트 순으로 정렬
        chats.sort(key=lambda c: c.updated_at, reverse=True)
        return chats
    
    def get_active_chat(self, user_id: str) -> Optional[Chat]:
        """사용자의 활성 채팅 가져오기"""
        active_chat_id = self.active_chats.get(user_id)
        if active_chat_id:
            return self.get_chat(active_chat_id)
        return None
    
    def set_active_chat(self, user_id: str, chat_id: str) -> bool:
        """활성 채팅 설정"""
        if chat_id not in self.chats:
            return False
        
        chat = self.chats[chat_id]
        if chat.user_id != user_id:
            return False
        
        with self._lock:
            # 기존 활성 채팅 비활성화
            old_active_id = self.active_chats.get(user_id)
            if old_active_id and old_active_id in self.chats:
                self.chats[old_active_id].active = False
            
            # 새 활성 채팅 설정
            self.active_chats[user_id] = chat_id
            chat.active = True
            
            log_message(f"활성 채팅 변경: {user_id} -> {chat_id}")
            return True
    
    def add_message(self, chat_id: str, message_type: str, content: str, code_blocks: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        채팅에 메시지 추가
        
        Args:
            chat_id: 채팅 ID
            message_type: 'user' 또는 'ai'
            content: 메시지 내용
            code_blocks: 코드 블록 리스트
            
        Returns:
            추가된 메시지 딕셔너리 또는 None
        """
        chat = self.get_chat(chat_id)
        if not chat:
            return None
        
        with self._lock:
            message = chat.add_message(message_type, content, code_blocks)
            
            # 백그라운드 저장 (즉시 저장하지 않고 마킹만)
            chat._needs_save = True
            
            return message
    
    def process_user_message(self, chat_id: str, user_message: str) -> Dict[str, Any]:
        """
        사용자 메시지를 처리하고 AI 응답 생성
        
        Args:
            chat_id: 채팅 ID
            user_message: 사용자 메시지
            
        Returns:
            AI 응답 딕셔너리
        """
        chat = self.get_chat(chat_id)
        if not chat:
            return {"success": False, "error": "채팅을 찾을 수 없습니다"}
        
        try:
            # 사용자 메시지 추가
            self.add_message(chat_id, "user", user_message)
            
            # AI 응답 생성 (module_AI 사용)
            ai_response = get_ai_response(user_message)
            
            if ai_response["success"]:
                # AI 응답 메시지 추가
                self.add_message(
                    chat_id, 
                    "ai", 
                    ai_response["content"], 
                    ai_response.get("code_blocks", [])
                )
                
                return {
                    "success": True,
                    "response": ai_response["content"],
                    "has_code": ai_response.get("has_code", False),
                    "code_blocks": ai_response.get("code_blocks", []),
                    "chat_title": chat.title
                }
            else:
                return {"success": False, "error": "AI 응답 생성 실패"}
                
        except Exception as e:
            log_message(f"메시지 처리 오류: {str(e)}")
            return {"success": False, "error": f"메시지 처리 중 오류: {str(e)}"}
    
    def analyze_error(self, chat_id: str, error_message: str, code: str = '', context: str = '') -> Dict[str, Any]:
        """
        에러 분석 요청 처리
        
        Args:
            chat_id: 채팅 ID
            error_message: 에러 메시지
            code: 관련 코드
            context: 컨텍스트
            
        Returns:
            에러 분석 결과
        """
        chat = self.get_chat(chat_id)
        if not chat:
            return {"success": False, "error": "채팅을 찾을 수 없습니다"}
        
        try:
            # 에러 분석 요청
            error_request = f"다음 에러를 분석해주세요:\n\n에러: {error_message}\n\n코드:\n```python\n{code}\n```"
            self.add_message(chat_id, "user", error_request)
            
            # AI 에러 분석
            analysis = analyze_code_error(error_message, code, context)
            
            # 분석 결과를 AI 메시지로 추가
            analysis_content = f"""에러 분석 결과입니다:

**🔍 오류 원인:**
{analysis['explanation']}

**💡 수정 방법:**
{analysis['suggested_fix']}

**🔧 수정된 코드:**
```python
{analysis['fixed_code']}
```"""
            
            self.add_message(chat_id, "ai", analysis_content)
            
            return {
                "success": True,
                "analysis": analysis_content,
                "suggested_fix": analysis['suggested_fix'],
                "fixed_code": analysis['fixed_code']
            }
            
        except Exception as e:
            log_message(f"에러 분석 오류: {str(e)}")
            return {"success": False, "error": f"에러 분석 중 오류: {str(e)}"}
    
    def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """
        채팅 삭제
        
        Args:
            chat_id: 채팅 ID
            user_id: 사용자 ID (권한 확인용)
            
        Returns:
            삭제 성공 여부
        """
        chat = self.get_chat(chat_id)
        if not chat or chat.user_id != user_id:
            return False
        
        with self._lock:
            # 메모리에서 제거
            del self.chats[chat_id]
            
            # 사용자 채팅 목록에서 제거
            if user_id in self.user_chats:
                self.user_chats[user_id] = [cid for cid in self.user_chats[user_id] if cid != chat_id]
            
            # 활성 채팅이었다면 제거
            if self.active_chats.get(user_id) == chat_id:
                del self.active_chats[user_id]
            
            # 파일 삭제
            chat_file = self._get_chat_file_path(chat_id)
            if os.path.exists(chat_file):
                os.remove(chat_file)
            
            self._save_index()
            
            log_message(f"채팅 삭제: {chat_id}")
            return True
    
    def clear_user_chats(self, user_id: str) -> int:
        """사용자의 모든 채팅 삭제"""
        user_chat_ids = self.user_chats.get(user_id, []).copy()
        deleted_count = 0
        
        for chat_id in user_chat_ids:
            if self.delete_chat(chat_id, user_id):
                deleted_count += 1
        
        return deleted_count
    
    def get_chat_stats(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """채팅 통계 가져오기"""
        chat = self.get_chat(chat_id)
        if not chat:
            return None
        
        return chat.stats.copy()
    
    def search_chats(self, user_id: str, query: str, limit: int = 10) -> List[Chat]:
        """채팅 검색 (제목 및 메시지 내용)"""
        user_chats = self.get_user_chats(user_id)
        results = []
        query_lower = query.lower()
        
        for chat in user_chats:
            # 제목 검색
            if query_lower in chat.title.lower():
                results.append(chat)
                continue
            
            # 메시지 내용 검색
            for message in chat.messages:
                if query_lower in message["content"].lower():
                    results.append(chat)
                    break
        
        return results[:limit]
    
    def _save_chat(self, chat: Chat) -> None:
        """개별 채팅 저장"""
        try:
            chat_file = self._get_chat_file_path(chat.id)
            with open(chat_file, 'w', encoding='utf-8') as f:
                f.write(chat.to_json())
            
            # 저장 완료 마킹
            if hasattr(chat, '_needs_save'):
                delattr(chat, '_needs_save')
                
        except Exception as e:
            log_message(f"채팅 저장 오류: {chat.id} - {str(e)}")
    
    def _save_index(self) -> None:
        """인덱스 파일 저장"""
        try:
            index_data = {
                "user_chats": self.user_chats,
                "active_chats": self.active_chats,
                "last_updated": datetime.now().isoformat()
            }
            
            index_file = self._get_index_file_path()
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            log_message(f"인덱스 저장 오류: {str(e)}")
    
    def _load_all_chats(self) -> None:
        """모든 채팅 로드"""
        try:
            # 인덱스 파일 로드
            index_file = self._get_index_file_path()
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    self.user_chats = index_data.get("user_chats", {})
                    self.active_chats = index_data.get("active_chats", {})
            
            # 개별 채팅 파일들 로드
            if os.path.exists(self.storage_path):
                for filename in os.listdir(self.storage_path):
                    if filename.endswith('.json') and filename != 'chat_index.json':
                        chat_id = filename[:-5]  # .json 제거
                        try:
                            chat_file = os.path.join(self.storage_path, filename)
                            with open(chat_file, 'r', encoding='utf-8') as f:
                                chat_data = json.load(f)
                                chat = Chat.from_dict(chat_data)
                                self.chats[chat.id] = chat
                        except Exception as e:
                            log_message(f"채팅 로드 오류: {filename} - {str(e)}")
            
            log_message(f"채팅 로드 완료: {len(self.chats)}개")
            
        except Exception as e:
            log_message(f"채팅 로드 오류: {str(e)}")
    
    def _start_auto_save_thread(self) -> None:
        """자동 저장 스레드 시작"""
        def auto_save_worker():
            while self._auto_save_enabled:
                try:
                    # 저장이 필요한 채팅들 찾기
                    chats_to_save = []
                    with self._lock:
                        for chat in self.chats.values():
                            if hasattr(chat, '_needs_save'):
                                chats_to_save.append(chat)
                    
                    # 백그라운드에서 저장
                    for chat in chats_to_save:
                        self._save_chat(chat)
                    
                    if chats_to_save:
                        log_message(f"자동 저장 완료: {len(chats_to_save)}개 채팅")
                    
                except Exception as e:
                    log_message(f"자동 저장 오류: {str(e)}")
                
                # 대기
                threading.Event().wait(self._auto_save_interval)
        
        auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        auto_save_thread.start()
        log_message("자동 저장 스레드 시작됨")
    
    def force_save_all(self) -> None:
        """모든 채팅 강제 저장"""
        with self._lock:
            for chat in self.chats.values():
                self._save_chat(chat)
            self._save_index()
        log_message(f"전체 저장 완료: {len(self.chats)}개 채팅")
    
    def cleanup_old_chats(self, days: int = 30) -> int:
        """오래된 채팅 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        old_chats = []
        
        for chat in self.chats.values():
            if chat.updated_at < cutoff_date:
                old_chats.append(chat)
        
        deleted_count = 0
        for chat in old_chats:
            if self.delete_chat(chat.id, chat.user_id):
                deleted_count += 1
        
        log_message(f"오래된 채팅 정리: {deleted_count}개 삭제")
        return deleted_count
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """매니저 통계"""
        total_messages = sum(len(chat.messages) for chat in self.chats.values())
        total_users = len(self.user_chats)
        
        return {
            "total_chats": len(self.chats),
            "total_users": total_users,
            "total_messages": total_messages,
            "active_chats": len(self.active_chats),
            "storage_path": self.storage_path
        }
    
    def shutdown(self) -> None:
        """매니저 종료 (모든 데이터 저장)"""
        self._auto_save_enabled = False
        self.force_save_all()
        log_message("채팅 매니저 종료됨")


# 전역 인스턴스
chat_manager = ChatManager()

def get_chat_manager() -> ChatManager:
    """전역 채팅 매니저 인스턴스 반환"""
    return chat_manager 