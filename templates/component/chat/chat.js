// ============================================
// 채팅 컴포넌트 JavaScript
// ============================================

class ChatManager {
    constructor() {
        this.currentChatId = null;
        this.chats = new Map();
        this.isTyping = false;
        this.messageHistory = [];
        this.settings = {
            model: 'gpt-4',
            temperature: 0.7,
            systemPrompt: '당신은 도움이 되는 AI 프로그래밍 어시스턴트입니다.'
        };
        
        this.init();
    }
    
    init() {
        console.log('💬 채팅 매니저 초기화 중...');
        this.loadChatHistory();
        this.setupEventListeners();
        this.setupAutoResize();
    }
    
    // ============================================
    // 채팅 히스토리 관리 (좌측 패널)
    // ============================================
    
    selectChat(chatId) {
        console.log('채팅 선택:', chatId);
        
        // 모든 채팅 비활성화
        this.chats.forEach(chat => chat.active = false);
        
        // 선택된 채팅 활성화
        const selectedChat = this.chats.find(chat => chat.id === chatId);
        if (selectedChat) {
            selectedChat.active = true;
            this.currentChatId = chatId;
            
            // 현재 메시지 히스토리를 선택된 채팅의 메시지로 변경
            this.messageHistory = selectedChat.messages || [];
            
            // UI 업데이트
            const titleElement = document.getElementById('currentChatTitle');
            if (titleElement) {
                titleElement.textContent = `💬 ${selectedChat.title}`;
            }
            
            // 채팅 히스토리 UI 업데이트
            this.renderChatHistory();
            
            // 메시지 로드
            this.loadChatMessages(chatId);
            
            console.log(`채팅 "${selectedChat.title}"로 전환됨, 메시지 ${selectedChat.messages?.length || 0}개`);
        } else {
            console.error('채팅을 찾을 수 없습니다:', chatId);
        }
    }
    
    async loadChatMessages(chatId) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        try {
            // 서버에서 채팅 메시지 가져오기
            const response = await fetch(`/api/chats/${chatId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                const chat = result.chat;
                
                // 메시지 컨테이너 초기화
                messagesContainer.innerHTML = '';
                
                // 서버에서 받은 메시지들 표시
                if (chat.messages && chat.messages.length > 0) {
                    chat.messages.forEach(msg => {
                        this.addMessage(msg.type, msg.content, msg.code_blocks);
                    });
                    
                    // 메시지 히스토리 업데이트
                    this.messageHistory = chat.messages;
                } else {
                    // 새 채팅인 경우 환영 메시지
                    const welcomeMsg = `안녕하세요! 👋 AI 코딩 어시스턴트입니다.

무엇을 도와드릴까요?

📝 **가능한 요청:**
• Python 코드 작성
• 에러 디버깅 및 수정
• 코드 리팩토링 및 최적화
• 데이터 분석 및 시각화
• 웹 스크래핑 (Selenium, BeautifulSoup)
• API 연동 및 자동화

💡 **팁:** 구체적으로 요청할수록 더 정확한 도움을 받을 수 있어요!`;
                    
                    this.addMessage('ai', welcomeMsg);
                    this.messageHistory = [{
                        type: 'ai',
                        content: welcomeMsg,
                        timestamp: new Date()
                    }];
                }
                
                console.log(`📄 채팅 메시지 로드됨: ${chat.messages?.length || 0}개`);
            } else {
                console.error('채팅 메시지 로드 실패:', result.error);
                messagesContainer.innerHTML = '<div class="error-message">❌ 채팅을 불러올 수 없습니다.</div>';
            }
            
        } catch (error) {
            console.error('채팅 메시지 로드 오류:', error);
            messagesContainer.innerHTML = '<div class="error-message">❌ 네트워크 오류가 발생했습니다.</div>';
        }
        
        this.scrollToBottom();
    }
    
    async loadChatHistory() {
        try {
            // 서버에서 채팅 목록 가져오기
            const response = await fetch('/api/chats', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.chats = result.chats || [];
                console.log(`💬 채팅 목록 로드됨: ${this.chats.length}개`);
            } else {
                console.error('채팅 목록 로드 실패:', result.error);
                this.chats = [];
            }
            
            this.renderChatHistory();
            
            // 활성 채팅이 있으면 선택, 없으면 첫 번째 채팅 선택
            const activeChat = this.chats.find(chat => chat.active);
            if (activeChat) {
                this.selectChat(activeChat.id);
            } else if (this.chats.length > 0) {
                this.selectChat(this.chats[0].id);
            } else {
                // 채팅이 없으면 새 채팅 생성
                this.createNewChat();
            }
            
        } catch (error) {
            console.error('채팅 목록 로드 오류:', error);
            this.chats = [];
            this.renderChatHistory();
        }
    }
    
    async createNewChat() {
        try {
            const response = await fetch('/api/chats', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: '새 채팅'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 새 채팅을 목록에 추가
                this.chats.unshift(result.chat);
                this.renderChatHistory();
                
                // 새 채팅 선택
                this.selectChat(result.chat.id);
                
                console.log('새 채팅 생성됨:', result.chat.id);
            } else {
                console.error('새 채팅 생성 실패:', result.error);
            }
            
        } catch (error) {
            console.error('새 채팅 생성 오류:', error);
        }
    }
    
    renderChatHistory() {
        const container = document.getElementById('chatHistoryList');
        if (!container) return;
        
        const chatsArray = this.chats;
        
        if (chatsArray.length === 0) {
            container.innerHTML = `
                <div class="no-chats">
                    <div style="text-align: center; padding: 2rem; color: #666;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💬</div>
                        <div>채팅이 없습니다</div>
                        <div style="font-size: 0.8rem; margin-top: 0.5rem;">새 채팅을 시작해보세요</div>
                    </div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = chatsArray.map(chat => `
            <div class="chat-item ${chat.active ? 'active' : ''}" onclick="selectChat('${chat.id}')">
                <div class="chat-info">
                    <div class="chat-title">${chat.title}</div>
                    <div class="chat-preview">${chat.preview}</div>
                </div>
                <div class="chat-meta">
                    <div class="chat-time">${chat.timestamp}</div>
                    <div class="chat-count">${chat.messageCount}</div>
                </div>
            </div>
        `).join('');
    }
    
    // ============================================
    // 채팅 인터페이스 관리 (우측 패널)
    // ============================================
    
    setupEventListeners() {
        // 입력 필드 이벤트
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.addEventListener('input', () => {
                this.updateCharCount();
                this.autoResizeTextarea();
            });
        }
        
        // 설정 슬라이더
        const tempSlider = document.getElementById('temperatureSlider');
        if (tempSlider) {
            tempSlider.addEventListener('input', (e) => {
                document.getElementById('temperatureValue').textContent = e.target.value;
                this.settings.temperature = parseFloat(e.target.value);
            });
        }
        
        // 모델 선택
        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                this.settings.model = e.target.value;
            });
        }
        
        // 시스템 프롬프트
        const systemPrompt = document.getElementById('systemPrompt');
        if (systemPrompt) {
            systemPrompt.addEventListener('change', (e) => {
                this.settings.systemPrompt = e.target.value;
            });
        }
    }
    
    setupAutoResize() {
        const textarea = document.getElementById('chatInput');
        if (!textarea) return;
        
        textarea.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
    }
    
    autoResizeTextarea() {
        const textarea = document.getElementById('chatInput');
        if (!textarea) return;
        
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
    }
    
    updateCharCount() {
        const chatInput = document.getElementById('chatInput');
        const charCount = document.getElementById('charCount');
        
        if (chatInput && charCount) {
            const count = chatInput.value.length;
            charCount.textContent = `${count}/2000`;
            
            if (count > 1800) {
                charCount.style.color = '#dc3545';
            } else if (count > 1500) {
                charCount.style.color = '#ffc107';
            } else {
                charCount.style.color = '#999';
            }
        }
    }
    
    // ============================================
    // 메시지 관리
    // ============================================
    
    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        if (!chatInput) return;
        
        const message = chatInput.value.trim();
        if (!message) return;
        
        // 사용자 메시지 추가
        this.addMessage('user', message);
        chatInput.value = '';
        this.updateCharCount();
        this.autoResizeTextarea();
        
        // 쇼핑 추천 패턴 체크
        const shoppingResponse = this.checkShoppingPatterns(message);
        if (shoppingResponse) {
            // 쇼핑 관련 질문이면 바로 응답
            this.showTypingIndicator();
            setTimeout(() => {
                this.hideTypingIndicator();
                this.addMessage('ai', shoppingResponse);
            }, 800); // 자연스러운 응답 지연
            return;
        }
        
        // AI 응답 요청
        this.showTypingIndicator();
        
        try {
            const response = await this.callAIAPI(message);
            this.hideTypingIndicator();
            
            if (response.success) {
                this.addMessage('ai', response.response, response.code_blocks);
            } else {
                this.addMessage('ai', `죄송합니다. 오류가 발생했습니다: ${response.error}`);
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('ai', `네트워크 오류가 발생했습니다: ${error.message}`);
        }
    }
    
    async callAIAPI(message) {
        /**
         * AI API 호출
         */
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                chat_id: this.currentChatId
            })
        });
        
        const result = await response.json();
        
        // 새 채팅이 생성된 경우 ID 업데이트
        if (result.success && result.chat_id) {
            this.currentChatId = result.chat_id;
            
            // 채팅 제목이 변경된 경우 UI 업데이트
            if (result.chat_title) {
                const titleElement = document.getElementById('currentChatTitle');
                if (titleElement) {
                    titleElement.textContent = `💬 ${result.chat_title}`;
                }
            }
        }
        
        return result;
    }
    
    addMessage(type, content, codeBlocks = []) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        const time = new Date().toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}-message`;
        
        if (type === 'user') {
            messageElement.innerHTML = `
                <div class="message-content">${this.formatMessage(content)}</div>
                <div class="message-time">${time}</div>
            `;
        } else {
            let codeBlocksHtml = '';
            if (codeBlocks && codeBlocks.length > 0) {
                codeBlocksHtml = codeBlocks.map(block => `
                    <div class="code-block-container">
                        <div class="code-block-header">
                            <span>🐍 Python 코드</span>
                            <div class="code-actions">
                                <button class="code-btn" onclick="copyCode('${block.id}')" title="코드 복사">📋</button>
                                <button class="code-btn execute-btn" onclick="executeCode('${block.id}')" title="코드 실행">▶️</button>
                                <button class="code-btn" onclick="addToNotebook('${block.id}')" title="노트북에 추가">📓</button>
                            </div>
                        </div>
                        <pre class="code-block" id="${block.id}"><code>${this.escapeHtml(block.code)}</code></pre>
                    </div>
                `).join('');
            }
            
            messageElement.innerHTML = `
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    ${this.formatMessage(content)}
                    ${codeBlocksHtml}
                </div>
                <div class="message-time">${time}</div>
            `;
        }
        
        // 타이핑 인디케이터 제거
        const typingIndicator = messagesContainer.querySelector('.typing');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
        
        // 메시지를 현재 활성 채팅에 저장
        const newMessage = { 
            type, 
            content, 
            code_blocks: codeBlocks, 
            timestamp: new Date() 
        };
        
        // 메시지 히스토리에 추가
        this.messageHistory.push(newMessage);
        
        // 현재 활성 채팅의 메시지 배열에도 추가
        const currentChat = this.chats.find(chat => chat.id === this.currentChatId);
        if (currentChat) {
            if (!currentChat.messages) {
                currentChat.messages = [];
            }
            currentChat.messages.push(newMessage);
            
            // 채팅 히스토리 UI 업데이트 (마지막 메시지 미리보기)
            currentChat.lastMessage = content.length > 50 ? content.substring(0, 50) + '...' : content;
            currentChat.time = new Date().toLocaleTimeString('ko-KR', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: true 
            });
            this.renderChatHistory();
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
        const typingElement = document.createElement('div');
        typingElement.className = 'message ai-message typing';
        typingElement.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingElement);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.querySelector('.message.typing');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    formatMessage(content) {
        // 코드 블록 처리
        content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        
        // 인라인 코드 처리
        content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 줄바꿈 처리
        content = content.replace(/\n/g, '<br>');
        
        return content;
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    generateSampleResponse(userMessage) {
        const responses = [
            "네, 도움을 드리겠습니다. 구체적으로 어떤 부분에서 도움이 필요하신가요?",
            "좋은 질문입니다! 이 문제를 해결하기 위해 몇 가지 방법을 제안드릴 수 있습니다.",
            "말씀하신 내용을 바탕으로 코드 예시를 준비해드리겠습니다.",
            "이 경우에는 다음과 같은 접근 방식을 권장합니다:\n\n1. 먼저 요구사항을 명확히 정의\n2. 적절한 라이브러리 선택\n3. 단계별 구현",
            "코드를 보여주시면 더 구체적인 피드백을 드릴 수 있습니다. 어떤 부분이 문제인지 알려주세요."
        ];
        
        return responses[Math.floor(Math.random() * responses.length)];
    }
    
    checkShoppingPatterns(message) {
        const msg = message.toLowerCase();
        
        // 기본 문구 패턴 (인사말, 도움 요청)
        if (msg.includes('안녕') || msg.includes('도와줘') || msg.includes('도움') || 
            msg.includes('뭐해') || msg.includes('뭘 할 수') || msg === '' || 
            msg.includes('무엇') || msg.includes('어떻게')) {
            return "무엇을 도와드릴까요?";
        }
        
        // 1. 무선 청소기 추천 요청
        if ((msg.includes('무선') || msg.includes('진공') || msg.includes('핸디')) && 
            (msg.includes('청소기') || msg.includes('청소') || msg.includes('먼지')) && 
            (msg.includes('추천') || msg.includes('사려고') || msg.includes('구매') || 
             msg.includes('종류') || msg.includes('많아'))) {
            const product = message.match(/(무선\s*청소기|진공\s*청소기|핸디\s*청소기|청소기)/i);
            const productName = product ? product[0] : '무선 청소기';
            return `네 그러면 먼저 상위 5개의 ${productName}를 찾아드리겠습니다.`;
        }
        
        // 2. 오래 팔린 제품 선호
        if ((msg.includes('상위') && msg.includes('평') && msg.includes('보다')) || 
            (msg.includes('오래') && (msg.includes('팔린') || msg.includes('판매'))) ||
            (msg.includes('2년') || msg.includes('오랫동안') || msg.includes('꾸준히'))) {
            return "네 2년 이상 된 제품을 기준으로 판매순으로 추천해드리겠습니다.";
        }
        
        // 3. 가볍고 빠른 배송 요청
        if ((msg.includes('가볍') || msg.includes('무게')) && 
            (msg.includes('빨리') || msg.includes('빠른') || msg.includes('로켓') || 
             msg.includes('배달') || msg.includes('배송'))) {
            return "네 로켓 배송 제품이면서 가벼운 것으로 추천해드리겠습니다.";
        }
        
        // 추가 쇼핑 관련 패턴들
        if (msg.includes('얼마') && (msg.includes('가격') || msg.includes('비용') || msg.includes('돈'))) {
            return "가격대를 말씀해주시면 그 범위 내에서 추천해드리겠습니다.";
        }
        
        if (msg.includes('브랜드') || msg.includes('제조사') || msg.includes('회사')) {
            return "선호하시는 브랜드가 있으시면 해당 브랜드 제품으로 추천해드리겠습니다.";
        }
        
        if (msg.includes('리뷰') || msg.includes('후기') || msg.includes('평점')) {
            return "높은 평점과 좋은 리뷰가 많은 제품들로 추천해드리겠습니다.";
        }
        
        return null; // 쇼핑 관련 패턴이 아님
    }
}

// ============================================
// 전역 함수들 (HTML에서 호출)
// ============================================

let chatManager = null;

// 채팅 매니저 초기화
function initializeChatManager() {
    if (!chatManager) {
        chatManager = new ChatManager();
    }
    return chatManager;
}

// 채팅 히스토리 새로고침
function refreshChatHistory() {
    console.log('채팅 히스토리 새로고침');
    if (chatManager) {
        chatManager.loadChatHistory();
    }
}

// 새 채팅 생성
function createNewChat() {
    if (chatManager) {
        console.log('새 채팅 생성 요청');
        chatManager.createNewChat();
    }
}

// 채팅 선택 (Global 함수)
function selectChat(chatId) {
    if (chatManager) {
        chatManager.selectChat(chatId);
    }
}

// 채팅 메시지 로드 (Global 함수 - deprecated, ChatManager 메소드 사용)
function loadChatMessages(chatId) {
    if (chatManager) {
        chatManager.loadChatMessages(chatId);
    }
}

// 채팅 검색 필터
function filterChats(searchTerm) {
    const chatItems = document.querySelectorAll('.chat-item');
    const term = searchTerm.toLowerCase();
    
    chatItems.forEach(item => {
        const title = item.querySelector('.chat-title').textContent.toLowerCase();
        const preview = item.querySelector('.chat-preview').textContent.toLowerCase();
        
        if (title.includes(term) || preview.includes(term)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

// 메시지 전송
function sendMessage() {
    if (chatManager) {
        chatManager.sendMessage();
    }
}

// 키보드 이벤트 처리
function handleChatKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 현재 채팅 지우기
function clearCurrentChat() {
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #666;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">💬</div>
                <div>새로운 대화를 시작해보세요</div>
            </div>
        `;
    }
    
    if (chatManager) {
        chatManager.messageHistory = [];
    }
}

// 채팅 설정 토글
function toggleChatSettings() {
    const settings = document.getElementById('chatSettings');
    if (settings) {
        if (settings.style.display === 'none') {
            settings.style.display = 'block';
        } else {
            settings.style.display = 'none';
        }
    }
}

// ============================================
// 코드 실행 관련 함수들
// ============================================

// 코드 복사
function copyCode(codeId) {
    const codeElement = document.getElementById(codeId);
    if (codeElement) {
        const code = codeElement.querySelector('code').textContent;
        navigator.clipboard.writeText(code).then(() => {
            showNotification('📋 코드가 클립보드에 복사되었습니다', 'success');
        }).catch(err => {
            console.error('코드 복사 실패:', err);
            showNotification('❌ 코드 복사에 실패했습니다', 'error');
        });
    }
}

// 코드 실행
async function executeCode(codeId) {
    const codeElement = document.getElementById(codeId);
    if (!codeElement) return;
    
    const code = codeElement.querySelector('code').textContent;
    const executeBtn = codeElement.parentElement.querySelector('.execute-btn');
    
    // 실행 중 상태로 변경
    executeBtn.innerHTML = '⏳';
    executeBtn.disabled = true;
    
    try {
        const response = await fetch('/api/ai/execute-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                auto_add_to_notebook: false
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 실행 결과 표시
            showCodeResult(codeId, result.result);
            showNotification('✅ 코드가 성공적으로 실행되었습니다', 'success');
        } else {
            showCodeResult(codeId, { error: result.error });
            showNotification('❌ 코드 실행 중 오류가 발생했습니다', 'error');
        }
        
    } catch (error) {
        showCodeResult(codeId, { error: error.message });
        showNotification('❌ 네트워크 오류가 발생했습니다', 'error');
    } finally {
        // 버튼 상태 복원
        executeBtn.innerHTML = '▶️';
        executeBtn.disabled = false;
    }
}

// 코드 실행 결과 표시
function showCodeResult(codeId, result) {
    const codeElement = document.getElementById(codeId);
    if (!codeElement) return;
    
    // 기존 결과 제거
    const existingResult = codeElement.parentElement.querySelector('.code-result');
    if (existingResult) {
        existingResult.remove();
    }
    
    // 새 결과 추가
    const resultDiv = document.createElement('div');
    resultDiv.className = 'code-result';
    
    if (result.error) {
        resultDiv.innerHTML = `
            <div class="result-header error">
                <span>❌ 실행 오류</span>
            </div>
            <pre class="result-content error">${result.error}</pre>
        `;
    } else {
        resultDiv.innerHTML = `
            <div class="result-header success">
                <span>✅ 실행 완료</span>
                ${result.execution_count ? `<span class="exec-count">[${result.execution_count}]</span>` : ''}
            </div>
            <pre class="result-content">${result.output || '(출력 없음)'}</pre>
        `;
    }
    
    codeElement.parentElement.appendChild(resultDiv);
}

// 노트북에 코드 추가
function addToNotebook(codeId) {
    const codeElement = document.getElementById(codeId);
    if (!codeElement) return;
    
    const code = codeElement.querySelector('code').textContent;
    
    // TODO: 노트북에 셀 추가 로직 구현
    console.log('노트북에 코드 추가:', code);
    showNotification('📓 노트북 연동 기능은 개발 중입니다', 'info');
}

// 알림 표시
function showNotification(message, type = 'info') {
    // 기존 알림 제거
    const existingNotification = document.querySelector('.chat-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `chat-notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 채팅 컴포넌트가 로드된 후 잠시 대기
    setTimeout(() => {
        if (document.getElementById('chatMessages') || document.getElementById('chatHistoryList')) {
            initializeChatManager();
        }
    }, 100);
}); 