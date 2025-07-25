"""
AI 코딩 어시스턴트 모듈
OpenAI API, Claude API 등과 연동하여 코딩 도움을 제공
"""

import os
import re
import json
import requests
from typing import List, Dict, Any, Optional
from MODULE.module_logger import log_message

class AIAssistant:
    def __init__(self, settings: Dict[str, Any] = None):
        """
        AI 어시스턴트 초기화
        
        Args:
            settings: AI 설정 (model, temperature, api_key 등)
        """
        self.settings = settings or {}
        self.model = self.settings.get('model', 'gpt-3.5-turbo')
        self.temperature = self.settings.get('temperature', 0.7)
        self.max_tokens = self.settings.get('max_tokens', 2000)
        self.system_prompt = self.settings.get('system_prompt', self._get_default_system_prompt())
        
        # API 키 설정
        self.api_key = self._get_api_key()
        self.base_url = self._get_base_url()
        
    def _get_api_key(self) -> Optional[str]:
        """API 키 가져오기 (환경변수 또는 설정에서)"""
        api_key = self.settings.get('api_key')
        if not api_key:
            # 모델에 따라 다른 환경변수 확인
            if 'gpt' in self.model.lower():
                api_key = os.getenv('OPENAI_API_KEY')
            elif 'claude' in self.model.lower():
                api_key = os.getenv('ANTHROPIC_API_KEY')
        
        return api_key
    
    def _get_base_url(self) -> str:
        """API 베이스 URL 가져오기"""
        if 'gpt' in self.model.lower():
            return 'https://api.openai.com/v1'
        elif 'claude' in self.model.lower():
            return 'https://api.anthropic.com/v1'
        else:
            return self.settings.get('base_url', 'https://api.openai.com/v1')
    
    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """당신은 전문적인 Python 프로그래밍 어시스턴트입니다.

주요 역할:
1. 파이썬 코드 작성 및 디버깅
2. 데이터 분석 및 시각화 
3. 웹 스크래핑 (Selenium, BeautifulSoup)
4. 파일 처리 및 자동화
5. API 연동 및 데이터베이스 작업

응답 규칙:
- 코드는 ```python 블록으로 감싸기
- 실행 가능한 완전한 코드 제공
- 주석으로 코드 설명 추가
- 에러 발생 시 해결 방법 제시
- 필요한 라이브러리 import 포함

현재 환경: Jupyter 스타일 노트북 환경에서 실행됩니다."""

    def chat(self, message: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        AI와 채팅
        
        Args:
            message: 사용자 메시지
            history: 채팅 히스토리
            
        Returns:
            AI 응답 딕셔너리
        """
        try:
            # 채팅 히스토리 준비
            messages = self._prepare_messages(message, history)
            
            # API 호출
            if 'gpt' in self.model.lower():
                response = self._call_openai_api(messages)
            elif 'claude' in self.model.lower():
                response = self._call_claude_api(messages)
            else:
                # 기본값으로 OpenAI 방식 사용
                response = self._call_openai_api(messages)
            
            # 응답 처리
            return self._process_response(response)
            
        except Exception as e:
            log_message(f"AI 채팅 오류: {str(e)}")
            return {
                'content': f"죄송합니다. AI 응답 중 오류가 발생했습니다: {str(e)}",
                'has_code': False,
                'code_blocks': [],
                'tokens_used': 0
            }
    
    def _prepare_messages(self, message: str, history: List[Dict] = None) -> List[Dict]:
        """채팅 메시지 준비"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # 히스토리 추가
        if history:
            for item in history[-10:]:  # 최근 10개만 사용
                if item.get('type') == 'user':
                    messages.append({"role": "user", "content": item['content']})
                elif item.get('type') == 'ai':
                    messages.append({"role": "assistant", "content": item['content']})
        
        # 현재 메시지 추가
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _call_openai_api(self, messages: List[Dict]) -> Dict:
        """OpenAI API 호출"""
        if not self.api_key:
            raise Exception("OpenAI API 키가 설정되지 않았습니다. 환경변수 OPENAI_API_KEY를 설정해주세요.")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API 오류: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _call_claude_api(self, messages: List[Dict]) -> Dict:
        """Claude API 호출"""
        if not self.api_key:
            raise Exception("Claude API 키가 설정되지 않았습니다. 환경변수 ANTHROPIC_API_KEY를 설정해주세요.")
        
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        # Claude는 system 메시지를 따로 처리
        system_msg = messages[0]['content'] if messages[0]['role'] == 'system' else ''
        conversation = messages[1:] if messages[0]['role'] == 'system' else messages
        
        data = {
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'system': system_msg,
            'messages': conversation
        }
        
        response = requests.post(
            f'{self.base_url}/messages',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API 오류: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _process_response(self, response: Dict) -> Dict[str, Any]:
        """API 응답 처리"""
        try:
            # OpenAI 응답 형식
            if 'choices' in response:
                content = response['choices'][0]['message']['content']
                tokens_used = response.get('usage', {}).get('total_tokens', 0)
            # Claude 응답 형식  
            elif 'content' in response:
                content = response['content'][0]['text']
                tokens_used = response.get('usage', {}).get('output_tokens', 0)
            else:
                raise Exception("알 수 없는 API 응답 형식")
            
            # 코드 블록 추출
            code_blocks = self._extract_code_blocks(content)
            has_code = len(code_blocks) > 0
            
            return {
                'content': content,
                'has_code': has_code,
                'code_blocks': code_blocks,
                'tokens_used': tokens_used
            }
            
        except Exception as e:
            raise Exception(f"응답 처리 오류: {str(e)}")
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """텍스트에서 코드 블록 추출"""
        code_blocks = []
        
        # ```python ... ``` 형식의 코드 블록 찾기
        pattern = r'```(?:python)?\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for i, code in enumerate(matches):
            code_blocks.append({
                'id': f'code_{i}',
                'language': 'python',
                'code': code.strip()
            })
        
        return code_blocks
    
    def analyze_error(self, error_message: str, code: str = '', context: str = '') -> Dict[str, str]:
        """에러 분석 및 수정 제안"""
        try:
            prompt = f"""다음 Python 코드에서 오류가 발생했습니다. 분석하고 수정 방법을 제안해주세요.

오류 메시지:
{error_message}

코드:
```python
{code}
```

컨텍스트:
{context}

다음 형식으로 답변해주세요:
1. 오류 원인 설명
2. 수정 방법
3. 수정된 코드 (```python 블록으로)
"""
            
            response = self.chat(prompt)
            
            # 수정된 코드 추출
            fixed_code = ''
            if response['code_blocks']:
                fixed_code = response['code_blocks'][0]['code']
            
            return {
                'explanation': response['content'],
                'suggested_fix': '수정된 코드를 확인해주세요.',
                'fixed_code': fixed_code
            }
            
        except Exception as e:
            log_message(f"에러 분석 오류: {str(e)}")
            return {
                'explanation': f"에러 분석 중 오류가 발생했습니다: {str(e)}",
                'suggested_fix': '',
                'fixed_code': ''
            }
    
    def suggest_improvements(self, code: str) -> Dict[str, str]:
        """코드 개선 제안"""
        try:
            prompt = f"""다음 Python 코드를 분석하고 개선 방법을 제안해주세요:

```python
{code}
```

다음 관점에서 분석해주세요:
1. 성능 최적화
2. 코드 가독성
3. 베스트 프랙티스
4. 에러 처리
5. 보안 고려사항

개선된 코드도 제공해주세요.
"""
            
            response = self.chat(prompt)
            
            improved_code = ''
            if response['code_blocks']:
                improved_code = response['code_blocks'][0]['code']
            
            return {
                'analysis': response['content'],
                'improved_code': improved_code
            }
            
        except Exception as e:
            log_message(f"코드 개선 제안 오류: {str(e)}")
            return {
                'analysis': f"코드 분석 중 오류가 발생했습니다: {str(e)}",
                'improved_code': ''
            }


# 설정 파일에서 기본 AI 설정 로드
def load_ai_config() -> Dict[str, Any]:
    """AI 설정 로드"""
    config_file = 'config/ai_config.json'
    
    default_config = {
        'model': 'gpt-3.5-turbo',
        'temperature': 0.7,
        'max_tokens': 2000,
        'timeout': 30
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_config.update(config)
    except Exception as e:
        log_message(f"AI 설정 로드 오류: {str(e)}")
    
    return default_config 