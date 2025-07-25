"""
개별 채팅 클래스
각 채팅 세션의 메시지, 상태, 설정을 관리
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class Chat:
    def __init__(self, chat_id: str = None, title: str = "새 채팅", user_id: str = None):
        """
        채팅 인스턴스 초기화
        
        Args:
            chat_id: 채팅 고유 ID (없으면 자동 생성)
            title: 채팅 제목
            user_id: 사용자 ID
        """
        self.id = chat_id or self._generate_chat_id()
        self.title = title
        self.user_id = user_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.active = False
        
        # 메시지 리스트
        self.messages: List[Dict[str, Any]] = []
        
        # 채팅 설정
        self.settings = {
            "model": "mock-ai",
            "temperature": 0.7,
            "max_tokens": 2000,
            "system_prompt": "Python 코딩 어시스턴트"
        }
        
        # 채팅 통계
        self.stats = {
            "message_count": 0,
            "user_message_count": 0,
            "ai_message_count": 0,
            "code_blocks_generated": 0,
            "last_activity": self.created_at
        }
    
    def _generate_chat_id(self) -> str:
        """고유한 채팅 ID 생성"""
        return f"chat_{uuid.uuid4().hex[:8]}"
    
    def add_message(self, message_type: str, content: str, code_blocks: List[Dict] = None) -> Dict[str, Any]:
        """
        채팅에 메시지 추가
        
        Args:
            message_type: 'user' 또는 'ai'
            content: 메시지 내용
            code_blocks: 코드 블록 리스트 (선택사항)
            
        Returns:
            추가된 메시지 딕셔너리
        """
        message = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "type": message_type,
            "content": content,
            "code_blocks": code_blocks or [],
            "timestamp": datetime.now(),
            "edited": False,
            "metadata": {}
        }
        
        self.messages.append(message)
        self._update_stats(message_type, code_blocks)
        self.updated_at = datetime.now()
        
        # 첫 번째 사용자 메시지로 제목 자동 설정
        if message_type == "user" and len(self.messages) == 1:
            self._auto_generate_title(content)
        
        return message
    
    def _update_stats(self, message_type: str, code_blocks: List[Dict] = None):
        """채팅 통계 업데이트"""
        self.stats["message_count"] += 1
        self.stats["last_activity"] = datetime.now()
        
        if message_type == "user":
            self.stats["user_message_count"] += 1
        elif message_type == "ai":
            self.stats["ai_message_count"] += 1
            if code_blocks:
                self.stats["code_blocks_generated"] += len(code_blocks)
    
    def _auto_generate_title(self, first_message: str) -> None:
        """첫 번째 메시지 기반으로 제목 자동 생성"""
        # 간단한 키워드 기반 제목 생성
        title_map = {
            "pandas": "📊 Pandas 데이터 분석",
            "matplotlib": "📈 데이터 시각화",
            "selenium": "🕷️ 웹 스크래핑",
            "flask": "🌐 Flask API 개발",
            "api": "🔗 API 개발",
            "크롤링": "🕸️ 웹 크롤링",
            "시각화": "📊 데이터 시각화",
            "그래프": "📈 차트 및 그래프"
        }
        
        first_message_lower = first_message.lower()
        for keyword, title in title_map.items():
            if keyword in first_message_lower:
                self.title = title
                return
        
        # 키워드가 없으면 첫 20자 + ...
        if len(first_message) > 20:
            self.title = first_message[:20] + "..."
        else:
            self.title = first_message
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """메시지 ID로 메시지 찾기"""
        for message in self.messages:
            if message["id"] == message_id:
                return message
        return None
    
    def edit_message(self, message_id: str, new_content: str) -> bool:
        """메시지 편집"""
        message = self.get_message_by_id(message_id)
        if message and message["type"] == "user":
            message["content"] = new_content
            message["edited"] = True
            message["edited_at"] = datetime.now()
            self.updated_at = datetime.now()
            return True
        return False
    
    def delete_message(self, message_id: str) -> bool:
        """메시지 삭제"""
        for i, message in enumerate(self.messages):
            if message["id"] == message_id:
                del self.messages[i]
                self.stats["message_count"] -= 1
                if message["type"] == "user":
                    self.stats["user_message_count"] -= 1
                elif message["type"] == "ai":
                    self.stats["ai_message_count"] -= 1
                self.updated_at = datetime.now()
                return True
        return False
    
    def clear_messages(self) -> None:
        """모든 메시지 삭제"""
        self.messages.clear()
        self.stats = {
            "message_count": 0,
            "user_message_count": 0,
            "ai_message_count": 0,
            "code_blocks_generated": 0,
            "last_activity": datetime.now()
        }
        self.updated_at = datetime.now()
    
    def get_message_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        메시지 히스토리 가져오기
        
        Args:
            limit: 최대 메시지 수 (None이면 전체)
            
        Returns:
            메시지 리스트
        """
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()
    
    def get_conversation_context(self, max_tokens: int = 2000) -> List[Dict[str, str]]:
        """
        AI 모델용 대화 컨텍스트 생성
        
        Args:
            max_tokens: 최대 토큰 수 (대략적)
            
        Returns:
            대화 컨텍스트 리스트
        """
        context = []
        estimated_tokens = 0
        
        # 최근 메시지부터 역순으로 추가
        for message in reversed(self.messages):
            content = message["content"]
            estimated_tokens += len(content.split()) * 1.3  # 대략적인 토큰 계산
            
            if estimated_tokens > max_tokens:
                break
            
            context.insert(0, {
                "role": "user" if message["type"] == "user" else "assistant",
                "content": content
            })
        
        return context
    
    def get_last_message_preview(self, max_length: int = 50) -> str:
        """마지막 메시지 미리보기"""
        if not self.messages:
            return "대화가 없습니다."
        
        last_message = self.messages[-1]
        content = last_message["content"]
        
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content
    
    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """채팅 설정 업데이트"""
        self.settings.update(new_settings)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """채팅 객체를 딕셔너리로 변환 (저장용)"""
        return {
            "id": self.id,
            "title": self.title,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active,
            "messages": [
                {
                    **msg,
                    "timestamp": msg["timestamp"].isoformat()
                } for msg in self.messages
            ],
            "settings": self.settings,
            "stats": {
                **self.stats,
                "last_activity": self.stats["last_activity"].isoformat()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chat':
        """딕셔너리에서 채팅 객체 생성 (로드용)"""
        chat = cls(
            chat_id=data["id"],
            title=data["title"],
            user_id=data.get("user_id")
        )
        
        chat.created_at = datetime.fromisoformat(data["created_at"])
        chat.updated_at = datetime.fromisoformat(data["updated_at"])
        chat.active = data["active"]
        chat.settings = data["settings"]
        
        # 메시지 복원
        chat.messages = []
        for msg_data in data["messages"]:
            msg = msg_data.copy()
            msg["timestamp"] = datetime.fromisoformat(msg_data["timestamp"])
            chat.messages.append(msg)
        
        # 통계 복원
        chat.stats = data["stats"].copy()
        chat.stats["last_activity"] = datetime.fromisoformat(data["stats"]["last_activity"])
        
        return chat
    
    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Chat':
        """JSON 문자열에서 채팅 객체 생성"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        return f"Chat(id={self.id}, title={self.title}, messages={len(self.messages)})"
    
    def __repr__(self) -> str:
        return self.__str__() 