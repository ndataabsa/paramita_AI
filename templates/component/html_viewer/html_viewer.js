// HTML 뷰어 컴포넌트
class HTMLViewer {
    constructor() {
        this.iframe = null;
        this.overlay = null;
        this.highlightMode = 'hover'; // 'hover' 또는 'click'
        this.currentHighlight = null;
        this.currentInfo = null;
        this.isInitialized = false;
        this.currentHTML = '';
        this.currentCSSList = []; // CSS 리스트 추가
        this.currentKernelId = null; // 현재 커널 ID
        this.currentHoveredElement = null; // 현재 호버된 요소
        this.contextMenu = null; // 우클릭 메뉴
        
        // 자동 새로고침 관련
        this.autoRefreshTimer = null;
        this.autoRefreshEnabled = false;
        this.lastScrollPosition = { x: 0, y: 0 };
        this.scrollSyncEnabled = true;  // 항상 활성화
        // scrollSyncHandler 제거됨 - 스크롤 이벤트 없음
        
        // API 중복 실행 방지
        this.isRefreshing = false;
        
        this.init();
    }
    
    init() {
        this.iframe = document.getElementById('htmlPreview');
        this.overlay = document.getElementById('previewOverlay');
        this.contextMenu = document.getElementById('contextMenu');
        
        // iframe 로드 완료 후 초기화
        this.iframe.addEventListener('load', () => {
                            // sandbox 속성 확인 및 재설정
                if (!this.iframe.getAttribute('sandbox') || !this.iframe.getAttribute('sandbox').includes('allow-scripts')) {
                    this.iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
                }
            
            this.setupElementHighlighting();
            this.setupContextMenu();
            // 스크롤 이벤트는 제거됨 - 새로고침 시에만 동기화
            this.isInitialized = true;
            this.updateStatus('ready', 'HTML 뷰어 준비됨');
            
            // CSS 적용 확인 (필요시만)
            try {
                const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
                const styleSheets = iframeDoc.styleSheets;
                if (styleSheets.length > 0) {
                    console.log('CSS 스타일시트 로드됨:', styleSheets.length + '개');
                }
            } catch (e) {
                // sandbox 제한으로 인한 정상적인 오류
            }
        });
        
        // 초기 상태 설정
        this.showNoContent();
        
        // 전역 우클릭 메뉴 숨기기
        document.addEventListener('click', () => {
            this.hideContextMenu();
        });
        
        // iframe으로부터 오는 메시지 처리
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'htmlViewerMenuAction') {
                console.log('iframe으로부터 메뉴 액션 수신:', event.data);
                this.handleIframeMenuMessage(event.data);
            }
        });
    }
    
    // 커널 ID 설정
    setKernelId(kernelId) {
        this.currentKernelId = kernelId;
        this.updateKernelInfo();
        this.updateStatus('ready', `커널 ID 설정됨: ${kernelId || '없음'}`);
    }
    
    // 커널 정보 업데이트
    updateKernelInfo() {
        const kernelInfo = document.getElementById('kernelInfo');
        if (kernelInfo) {
            kernelInfo.textContent = `커널: ${this.currentKernelId || '없음'}`;
        }
    }
    
    // 커널 ID 가져오기
    getKernelId() {
        return this.currentKernelId;
    }
    
    // 커널의 shared_dict 가져오기 (새로 구현)
    async getSharedDict() {
        if (!this.currentKernelId) {
            return null;
        }
        
        try {
            const response = await fetch(`/api/kernels/${this.currentKernelId}/shared-dict`);
            const data = await response.json();
            
            if (data.success && data.shared_dict) {
                return data.shared_dict;
            } else {
                return {};
            }
        } catch (error) {
            console.error('shared_dict 가져오기 실패:', error);
            return null;
        }
    }
    
    // 현재 커널의 shared_dict에 데이터 저장
    async setSharedDictValue(key, value) {
        if (!this.currentKernelId) {
            alert('커널이 없습니다. 먼저 커널을 생성해주세요.');
            return false;
        }
        
        try {
            // Python 코드로 shared_dict에 값 설정
            const code = `
if 'shared_dict' not in globals():
    shared_dict = {}
shared_dict['${key}'] = """${value}"""
print(f"shared_dict['${key}'] 설정 완료")
`;
            
            const response = await fetch(`/api/kernels/${this.currentKernelId}/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: code,
                    timeout: 30.0
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus('ready', `shared_dict['${key}'] 설정 완료`);
                return true;
            } else {
                alert('shared_dict 설정 실패: ' + (data.error || '알 수 없는 오류'));
                return false;
            }
        } catch (error) {
            console.error('shared_dict 설정 실패:', error);
            alert('shared_dict 설정 실패: ' + error.message);
            return false;
        }
    }
    
    // HTML 설정 (외부에서 호출)
        setHTML(htmlContent, cssList = []) {
        // 입력 값 타입 체크 및 변환
        if (htmlContent === null || htmlContent === undefined) {
            console.warn('HTML 내용이 null 또는 undefined입니다.');
            htmlContent = '';
        }
        
        // 문자열이 아닌 경우 문자열로 변환
        if (typeof htmlContent !== 'string') {
            console.warn('HTML 내용이 문자열이 아닙니다. 변환 중...');
            try {
                if (typeof htmlContent === 'object') {
                    htmlContent = JSON.stringify(htmlContent);
                } else {
                    htmlContent = String(htmlContent);
                }
                console.log('문자열 변환 완료');
            } catch (error) {
                console.error('HTML 내용을 문자열로 변환 실패:', error.message);
                htmlContent = '';
            }
        }
        
        // HTML 내용에서 외부 리소스 미리 제거
        let cleanedHTML = htmlContent;
        
        // 모든 script 태그 제거
        cleanedHTML = cleanedHTML.replace(/<script[^>]*>.*?<\/script>/gis, '<!-- script 태그 제거됨 -->');
        
        // 이미지 처리: 모든 이미지를 base64로 변환하므로 제거하지 않음
        // cleanedHTML = cleanedHTML.replace(/<img[^>]*>/gi, function(match) {
        //     // data URI로 시작하는 src는 허용
        //     if (match.includes('src="data:') || match.includes("src='data:")) {
        //         return match;
        //     }
        //     // 외부 URL은 제거
        //     return '<!-- 외부 이미지 제거됨 -->';
        // });
        
        // 모든 링크(a 태그) 제거
        cleanedHTML = cleanedHTML.replace(/<a[^>]*>.*?<\/a>/gis, (match) => {
            const content = match.replace(/<a[^>]*>/, '').replace(/<\/a>/, '');
            return `<span style="color: #007bff; text-decoration: underline; cursor: default;">${content}</span>`;
        });
        
        // 모든 iframe 태그 제거
        cleanedHTML = cleanedHTML.replace(
            /<iframe[^>]*>.*?<\/iframe>/gis,
            '<div style="border: 2px solid #ccc; padding: 20px; text-align: center; background: #f9f9f9; color: #666;">iframe (차단됨 - 보안상의 이유로)</div>'
        );
        
        // 외부 CSS 파일 링크 제거
        cleanedHTML = cleanedHTML.replace(
            /<link[^>]*rel=["']stylesheet["'][^>]*>/gi,
            '<!-- 외부 CSS 링크 제거됨 -->'
        );
        
        // 외부 스크립트 차단
        cleanedHTML = cleanedHTML.replace(
            /<script[^>]*src="[^"]*"[^>]*>.*?<\/script>/gis,
            '<!-- 외부 스크립트 차단됨 -->'
        );
        
        // 외부 리소스 참조 제거 (CSS background-image 등) - 이미지 변환하므로 비활성화
        // cleanedHTML = cleanedHTML.replace(
        //     /url\(['"]?(?!data:)[^'"]*\.(?:png|jpg|jpeg|gif|svg|webp|ico|css|js)['"]?\)/gi,
        //     'url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiBmaWxsPSIjRkZGRkZGIi8+CjxwYXRoIGQ9Ik04IDRMMTIgOEw4IDEyTDQgOEw4IDRaIiBmaWxsPSIjOTk5OTk5Ci8+Cjwvc3ZnPgo=")'
        // );
        
        this.currentHTML = cleanedHTML;
        this.currentCSSList = cssList || [];
        
        if (!cleanedHTML || cleanedHTML.trim() === '') {
            this.showNoContent();
            return;
        }
        
        this.renderHTML();
    }
    
    // HTML 렌더링 (CSS 포함)
    renderHTML() {
        if (!this.currentHTML || this.currentHTML.trim() === '') {
            this.showNoContent();
            return;
        }
        
        this.updateStatus('loading', '렌더링 중...');
        this.hideNoContent();
        
        try {
            // HTML 렌더링 시작 (이미 정리된 HTML 사용)
            let completeHTML = this.currentHTML;
            
            // SYSTEM_REQUEST에서 CSS 정보가 있는지 확인
            if (this.currentCSSList && this.currentCSSList.length > 0) {
                
                // CSS를 <style> 태그로 HTML에 삽입
                let cssContent = '';
                this.currentCSSList.forEach((cssItem, index) => {
                    if (cssItem.content) {
                        cssContent += `/* CSS ${index + 1}: ${cssItem.type} */\n`;
                        cssContent += cssItem.content + '\n\n';
                    }
                });
                
                if (cssContent) {
                    // CSS 내부의 외부 리소스 참조 차단 (data URI는 허용) - 이미지 변환하므로 비활성화
                    // cssContent = cssContent.replace(
                    //     /url\(['"]?(?!data:)[^'"]*\.(?:png|jpg|jpeg|gif|svg|webp|ico|css|js)['"]?\)/gi,
                    //     'url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiBmaWxsPSIjRkZGRkZGIi8+CjxwYXRoIGQ9Ik04IDRMMTIgOEw4IDEyTDQgOEw4IDRaIiBmaWxsPSIjOTk5OTk5Ci8+Cjwvc3ZnPgo=")'
                    // );
                    
                    // <head> 태그가 있으면 그 안에 삽입, 없으면 새로 생성
                    if (completeHTML.includes('<head>')) {
                        completeHTML = completeHTML.replace('<head>', '<head>\n<style>\n' + cssContent + '</style>');
                    } else {
                        // <head> 태그가 없으면 <html> 태그 다음에 삽입
                        if (completeHTML.includes('<html>')) {
                            completeHTML = completeHTML.replace('<html>', '<html>\n<head>\n<style>\n' + cssContent + '</style>\n</head>');
                        } else {
                            // <html> 태그도 없으면 맨 앞에 삽입
                            completeHTML = '<!DOCTYPE html>\n<html>\n<head>\n<style>\n' + cssContent + '</style>\n</head>\n<body>\n' + completeHTML + '\n</body>\n</html>';
                        }
                    }
                    console.log('CSS 포함됨:', cssContent.length + '자');
                }
            }
            
            // iframe을 새로 생성하여 sandbox 속성 문제 해결
            const newIframe = document.createElement('iframe');
            newIframe.id = this.iframe.id;
            newIframe.className = this.iframe.className;
            newIframe.style.cssText = this.iframe.style.cssText;
            // 보안 강화: 최소한의 권한만 허용
            newIframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
            newIframe.srcdoc = completeHTML;
            
            // 기존 iframe 교체
            this.iframe.parentNode.replaceChild(newIframe, this.iframe);
            this.iframe = newIframe;
            
            // 새로운 iframe에 이벤트 리스너 다시 설정
            this.iframe.addEventListener('load', () => {
                // sandbox 속성 확인 및 재설정
                if (!this.iframe.getAttribute('sandbox') || !this.iframe.getAttribute('sandbox').includes('allow-scripts')) {
                    this.iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
                }
                
                this.setupElementHighlighting();
                this.setupContextMenu();
                // 스크롤 이벤트는 제거됨 - 새로고침 시에만 동기화
                this.isInitialized = true;
                this.updateStatus('ready', 'HTML 뷰어 준비됨');
                
                // 스크롤 위치 복원
                this.restoreScrollPosition();
                
                // CSS 적용 확인 (필요시만)
                try {
                    const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
                    const styleSheets = iframeDoc.styleSheets;
                    if (styleSheets.length > 0) {
                        console.log('CSS 스타일시트 로드됨:', styleSheets.length + '개');
                    }
                } catch (e) {
                    // sandbox 제한으로 인한 정상적인 오류
                }
            });
            
            this.updateStatus('ready', 'HTML 렌더링 완료');
            // data URI 이미지 개수 확인
            const dataUriImageCount = (completeHTML.match(/src=["']data:image/g) || []).length;
            
            console.log(`HTML 렌더링 완료 (HTML: ${completeHTML.length}자, CSS: ${this.currentCSSList ? this.currentCSSList.length : 0}개, 이미지: ${dataUriImageCount}개)`);
            
        } catch (error) {
            console.error('HTML 렌더링 오류:', error.message);
            this.updateStatus('error', '렌더링 오류: ' + error.message);
        }
    }
    
    // Selenium 데이터 새로고침 (스크롤 위치 유지)
    async refreshSeleniumData() {
        // 중복 실행 방지
        if (this.isRefreshing) {
            console.log('⚠️ 이미 새로고침 중 - 요청 무시됨');
            return;
        }
        
        this.isRefreshing = true;
        console.log('Selenium 데이터 새로고침 시작 (스크롤 위치 유지)...');
        
        try {
            // 현재 스크롤 위치 저장
            this.saveScrollPosition();
            
            // 디버깅: 스크롤 위치와 커널 ID 확인
            console.log('🔍 디버깅 정보:');
            console.log('  - 커널 ID:', this.currentKernelId);
            console.log('  - 스크롤 위치:', this.lastScrollPosition);
            
            // 커널 ID 확인
            if (!this.currentKernelId) {
                console.error('❌ 커널 ID가 설정되지 않았습니다!');
                this.updateStatus('error', '커널 ID가 설정되지 않았습니다');
                return;
            }
            
            // SYSTEM_SELENIUM이 있는지 확인
            const sharedDict = await this.getSharedDict();
            if (sharedDict && sharedDict['SYSTEM_SELENIUM'] && sharedDict['SYSTEM_SELENIUM'].driver) {
                console.log('SYSTEM_SELENIUM 데이터를 새로고침합니다...');
                
                // 새로운 전용 API 사용 (스크롤 위치 포함)
                try {
                    const requestData = {
                        kernel_id: this.currentKernelId,
                        scroll_x: this.lastScrollPosition.x,
                        scroll_y: this.lastScrollPosition.y
                    };
                    
                    console.log('📤 API 요청 데이터:', requestData);
                    
                    const response = await fetch('/api/html-viewer/refresh-selenium', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(requestData)
                    });
                    
                    const result = await response.json();
                    
                    console.log('📥 API 응답:', result);
                    
                    if (result.success) {
                        console.log('SYSTEM_SELENIUM 새로고침 성공');
                        
                        // 스크롤 동기화 정보 로깅
                        if (result.scroll_synced) {
                            console.log('📜 Selenium 스크롤 동기화됨:', result.scroll_position);
                        }
                        
                        // 잠시 대기 후 HTML 뷰어 새로고침 (스크롤 위치는 자동 복원됨)
                        setTimeout(async () => {
                            const success = await this.loadHTMLFromSharedDict();
                            if (success) {
                                console.log('Selenium 데이터 새로고침 완료 (스크롤 위치 유지)');
                            }
                        }, 500);
                    } else {
                        console.log('SYSTEM_SELENIUM 새로고침 실패:', result.error);
                        // 기본 새로고침으로 fallback
                        const success = await this.loadHTMLFromSharedDict();
                        if (success) {
                            console.log('기본 Selenium 데이터 새로고침 완료');
                        }
                    }
                } catch (error) {
                    console.log('새로고침 API 오류:', error);
                    // 기본 새로고침으로 fallback
                    const success = await this.loadHTMLFromSharedDict();
                    if (success) {
                        console.log('기본 Selenium 데이터 새로고침 완료');
                    }
                } finally {
                    this.isRefreshing = false;
                }
            } else {
                console.log('SYSTEM_SELENIUM 드라이버가 없습니다. 기본 새로고침을 실행합니다.');
                // 기본 새로고침
                const success = await this.loadHTMLFromSharedDict();
                if (success) {
                    console.log('기본 Selenium 데이터 새로고침 완료');
                }
            }
        } catch (error) {
            console.log('Selenium 데이터 새로고침 중 오류:', error);
            // 기본 새로고침으로 fallback
            const success = await this.loadHTMLFromSharedDict();
            if (success) {
                console.log('기본 Selenium 데이터 새로고침 완료');
            }
        } finally {
            this.isRefreshing = false;
        }
    }
    
    // 새로고침 (수동, 현재 스크롤 위치 유지)
    async refreshView() {
        // 중복 실행 방지
        if (this.isRefreshing) {
            console.log('⚠️ 이미 새로고침 중 - 수동 요청 무시됨');
            return;
        }
        
        this.isRefreshing = true;
        console.log('수동 새로고침 시작...');
        
        try {
            // 수동 새로고침도 현재 스크롤 위치 저장 (0,0으로 초기화하지 않음)
            this.saveScrollPosition();
            
            // 디버깅: 수동 새로고침 정보
            console.log('🔍 수동 새로고침 디버깅:');
            console.log('  - 커널 ID:', this.currentKernelId);
            console.log('  - 현재 스크롤 위치:', this.lastScrollPosition);
            
            // 커널 ID 확인
            if (!this.currentKernelId) {
                console.error('❌ 커널 ID가 설정되지 않았습니다!');
                this.updateStatus('error', '커널 ID가 설정되지 않았습니다');
                return;
            }
            
            // SYSTEM_SELENIUM이 있는지 확인
            const sharedDict = await this.getSharedDict();
            if (sharedDict && sharedDict['SYSTEM_SELENIUM'] && sharedDict['SYSTEM_SELENIUM'].driver) {
                console.log('SYSTEM_SELENIUM 데이터를 새로고침합니다...');
                
                // 새로운 전용 API 사용 (스크롤 좌표 포함)
                try {
                    const requestData = {
                        kernel_id: this.currentKernelId,
                        scroll_x: this.lastScrollPosition.x,
                        scroll_y: this.lastScrollPosition.y
                    };
                    
                    console.log('📤 수동 새로고침 API 요청:', requestData);
                    
                    const response = await fetch('/api/html-viewer/refresh-selenium', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(requestData)
                    });
                    
                    const result = await response.json();
                    
                    console.log('📥 수동 새로고침 API 응답:', result);
                    
                    if (result.success) {
                        console.log('SYSTEM_SELENIUM 새로고침 성공');
                        
                        // 스크롤 동기화 정보 로깅
                        if (result.scroll_synced) {
                            console.log('📜 Selenium 스크롤 동기화됨:', result.scroll_position);
                        }
                        
                        // 잠시 대기 후 HTML 뷰어 새로고침 (스크롤 위치는 자동 복원됨)
                        setTimeout(async () => {
                            const success = await this.loadHTMLFromSharedDict();
                            if (success) {
                                console.log('Selenium 데이터 새로고침 완료 (스크롤 위치 유지)');
                            }
                        }, 500);
                    } else {
                        console.log('SYSTEM_SELENIUM 새로고침 실패:', result.error);
                        // 기본 새로고침으로 fallback
                        const success = await this.loadHTMLFromSharedDict();
                        if (success) {
                            console.log('기본 Selenium 데이터 새로고침 완료');
                        }
                    }
                } catch (error) {
                    console.log('새로고침 API 오류:', error);
                    // 기본 새로고침으로 fallback
                    const success = await this.loadHTMLFromSharedDict();
                    if (success) {
                        console.log('기본 Selenium 데이터 새로고침 완료');
                    }
                } finally {
                    this.isRefreshing = false;
                }
            } else {
                console.log('SYSTEM_SELENIUM 드라이버가 없습니다. 기본 새로고침을 실행합니다.');
                // 기본 새로고침
                const success = await this.loadHTMLFromSharedDict();
                if (success) {
                    console.log('기본 새로고침 완료');
                }
            }
        } catch (error) {
            console.log('새로고침 API 오류:', error);
            // 기본 새로고침으로 fallback
            const success = await this.loadHTMLFromSharedDict();
            if (success) {
                console.log('기본 Selenium 데이터 새로고침 완료');
            }
        } finally {
            this.isRefreshing = false;
        }
    }
    
    // 강제 새로고침 (init 변수 초기화 → 새로고침)
    async forceRefreshView() {
        // 중복 실행 방지
        if (this.isRefreshing) {
            console.log('⚠️ 이미 새로고침 중 - 강제 새로고침 요청 무시됨');
            return;
        }
        
        this.isRefreshing = true;
        console.log('🔴 강제 새로고침 시작 (init 초기화 + 이미지 재변환)...');
        
        try {
            // 커널 ID 확인
            if (!this.currentKernelId) {
                console.error('❌ 커널 ID가 설정되지 않았습니다!');
                this.updateStatus('error', '커널 ID가 설정되지 않았습니다');
                return;
            }
            
            // 1단계: init 변수 초기화
            console.log('🔄 1단계: HTML 변환 초기화 중...');
            this.updateStatus('loading', 'HTML 변환 초기화 중...');
            
            try {
                const resetResponse = await fetch('/api/html-viewer/reset-init', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        kernel_id: this.currentKernelId
                    })
                });
                
                const resetResult = await resetResponse.json();
                console.log('📥 init 초기화 API 응답:', resetResult);
                
                if (resetResult.success) {
                    console.log('✅ HTML 변환 초기화 완료');
                    console.log('  - 이전 상태:', resetResult.details.old_value);
                    console.log('  - 새 상태:', resetResult.details.new_value); 
                    console.log('  - 캐시 정리:', resetResult.details.cache_cleared);
                } else {
                    console.warn('⚠️ init 초기화 실패, 계속 진행:', resetResult.error);
                }
                
            } catch (error) {
                console.warn('⚠️ init 초기화 API 오류, 계속 진행:', error);
            }
            
            // 2단계: 일반 새로고침 실행 (init이 False로 설정되어 이미지 재변환 실행됨)
            console.log('🔄 2단계: 새로고침 실행 중...');
            this.updateStatus('loading', '강제 새로고침 중...');
            
            // 현재 스크롤 위치 저장
            this.saveScrollPosition();
            
            // SYSTEM_SELENIUM이 있는지 확인
            const sharedDict = await this.getSharedDict();
            if (sharedDict && sharedDict['SYSTEM_SELENIUM'] && sharedDict['SYSTEM_SELENIUM'].driver) {
                console.log('SYSTEM_SELENIUM 데이터를 강제 새로고침합니다...');
                
                try {
                    const requestData = {
                        kernel_id: this.currentKernelId,
                        scroll_x: this.lastScrollPosition.x,
                        scroll_y: this.lastScrollPosition.y
                    };
                    
                    console.log('📤 강제 새로고침 API 요청:', requestData);
                    
                    const refreshResponse = await fetch('/api/html-viewer/refresh-selenium', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(requestData)
                    });
                    
                    const refreshResult = await refreshResponse.json();
                    console.log('📥 강제 새로고침 API 응답:', refreshResult);
                    
                    if (refreshResult.success) {
                        console.log('✅ SYSTEM_SELENIUM 강제 새로고침 성공');
                        
                        // 스크롤 동기화 정보 로깅
                        if (refreshResult.scroll_synced) {
                            console.log('📜 Selenium 스크롤 동기화됨:', refreshResult.scroll_position);
                        }
                        
                        // 잠시 대기 후 HTML 뷰어 새로고침
                        setTimeout(async () => {
                            const success = await this.loadHTMLFromSharedDict();
                            if (success) {
                                console.log('🎉 강제 새로고침 완료 (이미지 재변환됨)');
                                this.updateStatus('ready', '강제 새로고침 완료 (이미지 재변환됨)');
                            }
                        }, 500);
                    } else {
                        console.log('❌ SYSTEM_SELENIUM 강제 새로고침 실패:', refreshResult.error);
                        // 기본 새로고침으로 fallback
                        const success = await this.loadHTMLFromSharedDict();
                        if (success) {
                            console.log('기본 강제 새로고침 완료');
                            this.updateStatus('ready', '기본 강제 새로고침 완료');
                        }
                    }
                } catch (error) {
                    console.log('강제 새로고침 API 오류:', error);
                    // 기본 새로고침으로 fallback
                    const success = await this.loadHTMLFromSharedDict();
                    if (success) {
                        console.log('기본 강제 새로고침 완료');
                        this.updateStatus('ready', '기본 강제 새로고침 완료');
                    }
                }
            } else {
                console.log('SYSTEM_SELENIUM 드라이버가 없습니다. 기본 강제 새로고침을 실행합니다.');
                // 기본 새로고침
                const success = await this.loadHTMLFromSharedDict();
                if (success) {
                    console.log('기본 강제 새로고침 완료');
                    this.updateStatus('ready', '기본 강제 새로고침 완료');
                }
            }
            
        } catch (error) {
            console.error('❌ 강제 새로고침 전체 오류:', error);
            this.updateStatus('error', '강제 새로고침 오류: ' + error.message);
        } finally {
            this.isRefreshing = false;
        }
    }
    
    // 뷰 지우기
    clearView() {
        this.currentHTML = '';
        this.clearHighlight();
        // currentHoveredElement는 유지 (마지막 선택한 요소 보존)
        this.showNoContent();
        this.updateStatus('ready', '뷰가 지워졌습니다');
    }
    
    // 내용 없음 표시
    showNoContent() {
        const noContent = document.getElementById('noContent');
        if (noContent) {
            noContent.style.display = 'flex';
        }
        if (this.iframe) {
            this.iframe.style.display = 'none';
        }
    }
    
    // 내용 없음 숨기기
    hideNoContent() {
        const noContent = document.getElementById('noContent');
        if (noContent) {
            noContent.style.display = 'none';
        }
        if (this.iframe) {
            this.iframe.style.display = 'block';
        }
    }
    
    // 요소 하이라이팅 설정 (구글 크롬 스타일)
    setupElementHighlighting() {
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            
            // iframe 내부 스크롤 이벤트 감지 (디바운싱 적용)
            let scrollTimeout;
            iframeDoc.addEventListener('scroll', () => {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    if (this.currentHighlight && this.currentHoveredElement) {
                        // 현재 하이라이트된 요소의 위치를 업데이트
                        this.highlightElement(this.currentHoveredElement, {});
                    }
                }, 10); // 10ms 디바운싱
            });
            
            // iframe 윈도우 리사이즈 이벤트도 감지
            const iframeWindow = this.iframe.contentWindow;
            if (iframeWindow) {
                iframeWindow.addEventListener('resize', () => {
                    if (this.currentHighlight && this.currentHoveredElement) {
                        this.highlightElement(this.currentHoveredElement, {});
                    }
                });
            }
            
            // 모든 요소에 호버 이벤트 추가
            const allElements = iframeDoc.querySelectorAll('*');
            allElements.forEach(element => {
                // 호버 이벤트
                element.addEventListener('mouseenter', (e) => {
                    if (this.highlightMode === 'hover') {
                        this.highlightElement(element, e);
                        this.currentHoveredElement = element;
                    }
                });
                
                element.addEventListener('mouseleave', (e) => {
                    if (this.highlightMode === 'hover') {
                        this.clearHighlight();
                        // currentHoveredElement는 유지 (마지막 선택한 요소 보존)
                    }
                });
                
                // 클릭 이벤트
                element.addEventListener('click', (e) => {
                    if (this.highlightMode === 'click') {
                        e.preventDefault();
                        e.stopPropagation();
                        this.highlightElement(element, e);
                        this.currentHoveredElement = element;
                    }
                });
                
                // 우클릭 이벤트
                element.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showIframeContextMenu(e, element);
                });
            });
            
            this.updateStatus('ready', '요소 하이라이팅 활성화됨');
        } catch (error) {
            // sandbox 제한으로 인한 정상적인 오류
        }
    }
    
    // 요소 하이라이팅 (구글 크롬 스타일)
    highlightElement(element, event) {
        this.clearHighlight();
        
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            const iframeRect = this.iframe.getBoundingClientRect();
            
            // iframe 내부의 스크롤 위치 정확히 계산
            const iframeScrollX = iframeDoc.documentElement.scrollLeft || iframeDoc.body.scrollLeft || 0;
            const iframeScrollY = iframeDoc.documentElement.scrollTop || iframeDoc.body.scrollTop || 0;
            
            // 요소의 정확한 위치 계산 (스크롤 고려)
            const elementRect = element.getBoundingClientRect();
            
            // iframe 내부 좌표를 부모 좌표로 변환 (스크롤 고려)
            const highlightRect = {
                left: iframeRect.left + elementRect.left,
                top: iframeRect.top + elementRect.top,
                width: elementRect.width,
                height: elementRect.height
            };
            
            // 하이라이트 요소 생성 (구글 크롬 스타일)
            this.currentHighlight = document.createElement('div');
            this.currentHighlight.className = 'element-highlight';
            this.currentHighlight.style.position = 'fixed';
            this.currentHighlight.style.left = highlightRect.left + 'px';
            this.currentHighlight.style.top = highlightRect.top + 'px';
            this.currentHighlight.style.width = highlightRect.width + 'px';
            this.currentHighlight.style.height = highlightRect.height + 'px';
            this.currentHighlight.style.pointerEvents = 'none';
            this.currentHighlight.style.zIndex = '10000';
            
            // 정보 툴팁 생성
            this.currentInfo = document.createElement('div');
            this.currentInfo.className = 'element-info';
            this.currentInfo.style.position = 'fixed';
            this.currentInfo.style.zIndex = '10001';
            
            const elementInfo = this.getElementInfo(element);
            this.currentInfo.innerHTML = `
                <strong>${element.tagName.toLowerCase()}</strong><br>
                ${elementInfo.classes ? `클래스: ${elementInfo.classes}<br>` : ''}
                ${elementInfo.id ? `ID: ${elementInfo.id}<br>` : ''}
                크기: ${Math.round(elementRect.width)}×${Math.round(elementRect.height)}px
            `;
            
            // 툴팁 위치 계산 (화면 경계 고려)
            let tooltipX = highlightRect.left;
            let tooltipY = highlightRect.top - 60;
            
            // 오른쪽 경계 체크
            if (tooltipX + 200 > window.innerWidth) {
                tooltipX = window.innerWidth - 220;
            }
            
            // 위쪽 경계 체크
            if (tooltipY < 0) {
                tooltipY = highlightRect.bottom + 10;
            }
            
            this.currentInfo.style.left = tooltipX + 'px';
            this.currentInfo.style.top = tooltipY + 'px';
            
            // DOM에 추가
            document.body.appendChild(this.currentHighlight);
            document.body.appendChild(this.currentInfo);
            
        } catch (error) {
            // 하이라이팅 실패 (정상적인 오류)
        }
    }
    
    // 하이라이트 제거
    clearHighlight() {
        if (this.currentHighlight) {
            this.currentHighlight.remove();
            this.currentHighlight = null;
        }
        if (this.currentInfo) {
            this.currentInfo.remove();
            this.currentInfo = null;
        }
    }
    
    // 요소 정보 추출
    getElementInfo(element) {
        const info = {
            tagName: element.tagName.toLowerCase(),
            classes: element.className ? element.className.split(' ').filter(c => c.trim()).join(', ') : null,
            id: element.id || null,
            text: element.textContent ? element.textContent.trim().substring(0, 50) + (element.textContent.length > 50 ? '...' : '') : null
        };
        
        return info;
    }
    
    // 우클릭 메뉴 설정
    setupContextMenu() {
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            
            // iframe 내부에 컨텍스트 메뉴 생성
            this.createIframeContextMenu(iframeDoc);
            
            // iframe 내부에서 우클릭 시 메뉴 표시
            iframeDoc.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                console.log('iframe 내부 우클릭 감지됨:', {
                    clientX: e.clientX,
                    clientY: e.clientY
                });
                
                this.showIframeContextMenu(e, e.target);
            });
            
        } catch (error) {
            // sandbox 제한으로 인한 정상적인 오류
        }
    }
    
    // iframe 내부에 컨텍스트 메뉴 생성
    createIframeContextMenu(iframeDoc) {
        // 기존 메뉴가 있으면 제거
        const existingMenu = iframeDoc.getElementById('iframeContextMenu');
        if (existingMenu) {
            existingMenu.remove();
        }
        
        // 새로운 컨텍스트 메뉴 생성
        const contextMenu = iframeDoc.createElement('div');
        contextMenu.id = 'iframeContextMenu';
        contextMenu.style.cssText = `
            position: fixed;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 10000;
            display: none;
            font-family: Arial, sans-serif;
            font-size: 14px;
            min-width: 150px;
        `;
        
        // 메뉴 아이템들 생성
        const menuItems = [
            { 
                text: '복사', 
                action: 'showCopySubmenu',
                submenu: [
                    { text: 'XPath 복사', action: 'copyXPath' },
                    { text: 'Full XPath 복사', action: 'copyFullXPath' },
                    { text: 'CSS 선택자 복사', action: 'copyCSSSelector' },
                    { text: 'ID 복사', action: 'copyElementId' },
                    { text: '클래스 복사', action: 'copyElementClass' },
                    { text: 'HTML 복사', action: 'copyElementHTML' },
                    { text: '텍스트 복사', action: 'copyElementText' }
                ]
            },
            { 
                text: '요소 복사', 
                action: 'showElementCopySubmenu',
                submenu: [
                    { text: '해당 요소만 복사', action: 'copyElementOnly' },
                    { text: '자식 모두 복사', action: 'copyElementWithChildren' }
                ]
            },
            { 
                text: '수집 셀 추가', 
                action: 'showCollectSubmenu',
                submenu: [
                    { text: 'ID로 수집', action: 'collectById' },
                    { text: '클래스로 수집', action: 'collectByClass' },
                    { text: 'XPath로 수집', action: 'collectByXPath' }
                ]
            },
            { text: '요소 검사', action: 'inspectElement' }
        ];
        
        menuItems.forEach(item => {
            const menuItem = iframeDoc.createElement('div');
            menuItem.style.cssText = `
                padding: 8px 12px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
                transition: background-color 0.2s;
                position: relative;
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;
            
            // 메뉴 텍스트
            const menuText = iframeDoc.createElement('span');
            menuText.textContent = item.text;
            menuItem.appendChild(menuText);
            
            // 서브메뉴가 있는 경우 화살표 추가
            if (item.submenu) {
                const arrow = iframeDoc.createElement('span');
                arrow.textContent = '▶';
                arrow.style.cssText = `
                    font-size: 10px;
                    color: #666;
                    margin-left: 8px;
                `;
                menuItem.appendChild(arrow);
                
                // 서브메뉴 생성
                const submenu = iframeDoc.createElement('div');
                submenu.style.cssText = `
                    position: absolute;
                    left: 100%;
                    top: 0;
                    background: white;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                    display: none;
                    min-width: 150px;
                    z-index: 10001;
                `;
                
                // 서브메뉴 위치 조정 함수
                const adjustSubmenuPosition = () => {
                    const menuRect = menuItem.getBoundingClientRect();
                    const viewportWidth = iframeDoc.documentElement.clientWidth || iframeDoc.body.clientWidth;
                    
                    // 오른쪽 공간이 부족하면 왼쪽에 표시
                    if (menuRect.right + 150 > viewportWidth) {
                        submenu.style.left = 'auto';
                        submenu.style.right = '100%';
                    } else {
                        submenu.style.left = '100%';
                        submenu.style.right = 'auto';
                    }
                };
                
                item.submenu.forEach(subItem => {
                    const subMenuItem = iframeDoc.createElement('div');
                    subMenuItem.textContent = subItem.text;
                    subMenuItem.style.cssText = `
                        padding: 8px 12px;
                        cursor: pointer;
                        border-bottom: 1px solid #eee;
                        transition: background-color 0.2s;
                    `;
                    
                    // 서브메뉴 호버 효과
                    subMenuItem.addEventListener('mouseenter', () => {
                        subMenuItem.style.backgroundColor = '#f0f0f0';
                    });
                    
                    subMenuItem.addEventListener('mouseleave', () => {
                        subMenuItem.style.backgroundColor = 'white';
                    });
                    
                    // 서브메뉴 클릭 이벤트
                    subMenuItem.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const currentElement = this.currentHoveredElement;
                        // 서브메뉴 클릭
                        
                        // iframe 내부에서 직접 복사 기능 실행
                        if (iframeDoc.executeCopyAction) {
                            iframeDoc.executeCopyAction(subItem.action, currentElement);
                        }
                        
                        // 메뉴 숨기기
                        const contextMenu = document.getElementById('iframeContextMenu');
                        if (contextMenu) {
                            contextMenu.style.display = 'none';
                        }
                    });
                    
                    submenu.appendChild(subMenuItem);
                });
                
                // 마지막 서브메뉴 아이템의 border 제거
                const lastSubItem = submenu.lastElementChild;
                if (lastSubItem) {
                    lastSubItem.style.borderBottom = 'none';
                }
                
                contextMenu.appendChild(submenu);
                
                // 메인 메뉴 호버 시 서브메뉴 표시
                menuItem.addEventListener('mouseenter', () => {
                    menuItem.style.backgroundColor = '#f0f0f0';
                    submenu.style.display = 'block';
                    adjustSubmenuPosition();
                });
                
                menuItem.addEventListener('mouseleave', () => {
                    menuItem.style.backgroundColor = 'white';
                    // 약간의 지연으로 서브메뉴로 마우스 이동 가능하게
                    setTimeout(() => {
                        if (!submenu.matches(':hover')) {
                            submenu.style.display = 'none';
                        }
                    }, 100);
                });
                
                // 서브메뉴 호버 시 유지
                submenu.addEventListener('mouseenter', () => {
                    submenu.style.display = 'block';
                });
                
                submenu.addEventListener('mouseleave', () => {
                    submenu.style.display = 'none';
                });
            } else {
                // 일반 메뉴 아이템
                menuItem.addEventListener('mouseenter', () => {
                    menuItem.style.backgroundColor = '#f0f0f0';
                });
                
                menuItem.addEventListener('mouseleave', () => {
                    menuItem.style.backgroundColor = 'white';
                });
                
                // 클릭 이벤트
                menuItem.addEventListener('click', () => {
                    const currentElement = this.currentHoveredElement;
                    // 메인 메뉴 클릭
                    
                    // iframe 내부에서 직접 복사 기능 실행
                    if (iframeDoc.executeCopyAction) {
                        iframeDoc.executeCopyAction(item.action, currentElement);
                    }
                    
                    // 메뉴 숨기기
                    const contextMenu = document.getElementById('iframeContextMenu');
                    if (contextMenu) {
                        contextMenu.style.display = 'none';
                    }
                });
            }
            
            contextMenu.appendChild(menuItem);
        });
        
        // 마지막 아이템의 border 제거
        const lastItem = contextMenu.lastElementChild;
        if (lastItem) {
            lastItem.style.borderBottom = 'none';
        }
        
        // iframe body에 메뉴 추가
        iframeDoc.body.appendChild(contextMenu);
        
        // iframe 내부 클릭 시 메뉴 숨기기
        iframeDoc.addEventListener('click', () => {
            this.hideIframeContextMenu();
        });
        
        // iframe 내부에서 복사 기능 실행하는 메서드 추가
        iframeDoc.executeCopyAction = (action, element) => {
            if (!element) {
                return;
            }
            
            try {
                let textToCopy = '';
                
                switch (action) {
                    case 'copyXPath':
                        textToCopy = this.getElementXPath(element);
                        break;
                    case 'copyFullXPath':
                        textToCopy = this.getElementFullXPath(element);
                        break;
                    case 'copyCSSSelector':
                        textToCopy = this.getElementCSSSelector(element);
                        break;
                    case 'copyElementId':
                        textToCopy = element.id || '';
                        break;
                    case 'copyElementClass':
                        textToCopy = element.className || '';
                        break;
                    case 'copyElementHTML':
                        textToCopy = element.outerHTML;
                        break;
                    case 'copyElementText':
                        textToCopy = element.textContent || element.innerText || '';
                        break;
                    case 'copyElementOnly':
                        const tagName = element.tagName.toLowerCase();
                        const id = element.id ? ` id="${element.id}"` : '';
                        const className = element.className ? ` class="${element.className}"` : '';
                        textToCopy = `<${tagName}${id}${className}></${tagName}>`;
                        break;
                    case 'copyElementWithChildren':
                        textToCopy = element.outerHTML;
                        break;
                    case 'inspectElement':
                        const info = this.getElementInfo(element);
                        console.log('요소 정보:', info);
                        return;
                    default:
                        return;
                }
                
                // 임시 텍스트 영역을 만들어서 복사
                const textArea = document.createElement('textarea');
                textArea.value = textToCopy;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {
                    const successful = document.execCommand('copy');
                    if (successful) {
                        console.log('복사 완료:', textToCopy.substring(0, 100) + (textToCopy.length > 100 ? '...' : ''));
                    } else {
                        console.log('복사 실패');
                    }
                } catch (err) {
                    console.error('복사 실패:', err);
                } finally {
                    document.body.removeChild(textArea);
                }
                
                            } catch (error) {
                    console.error('복사 처리 중 오류:', error);
                }
        };
        
        // iframe 내부 컨텍스트 메뉴 생성 완료
    }
    
    // iframe 내부 컨텍스트 메뉴 표시
    showIframeContextMenu(event, element) {
        // 현재 선택된 요소 저장
        this.currentHoveredElement = element;
        
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            const contextMenu = iframeDoc.getElementById('iframeContextMenu');
            
            if (contextMenu) {
                // 메뉴 위치 설정
                contextMenu.style.left = event.clientX + 'px';
                contextMenu.style.top = event.clientY + 'px';
                contextMenu.style.display = 'block';
                
                // iframe 내부 메뉴 표시
                
                // 화면 경계 체크
                setTimeout(() => {
                    const rect = contextMenu.getBoundingClientRect();
                    const viewportWidth = iframeDoc.documentElement.clientWidth || iframeDoc.body.clientWidth;
                    const viewportHeight = iframeDoc.documentElement.clientHeight || iframeDoc.body.clientHeight;
                    
                    // 오른쪽 경계 체크
                    if (rect.right > viewportWidth) {
                        contextMenu.style.left = (event.clientX - rect.width) + 'px';
                    }
                    
                    // 아래쪽 경계 체크
                    if (rect.bottom > viewportHeight) {
                        contextMenu.style.top = (event.clientY - rect.height) + 'px';
                    }
                    
                    // 왼쪽 경계 체크
                    if (rect.left < 0) {
                        contextMenu.style.left = '0px';
                    }
                    
                    // 위쪽 경계 체크
                    if (rect.top < 0) {
                        contextMenu.style.top = '0px';
                    }
                }, 0);
            }
        } catch (error) {
            // 메뉴 표시 실패 (정상적인 오류)
        }
    }
    
    // iframe 내부 컨텍스트 메뉴 숨기기
    hideIframeContextMenu() {
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            const contextMenu = iframeDoc.getElementById('iframeContextMenu');
            if (contextMenu) {
                contextMenu.style.display = 'none';
            }
        } catch (error) {
            // 메뉴 숨기기 실패 (정상적인 오류)
        }
    }
    
    // iframe 내부 메뉴 액션 처리
    handleIframeMenuAction(action, element = null) {
        // 요소가 전달되지 않으면 현재 하이라이트된 요소 사용
        const targetElement = element || this.currentHoveredElement;
        
        switch (action) {
            // 복사 관련
            case 'copyXPath':
                this.copyElementXPath(targetElement);
                break;
            case 'copyCSSSelector':
                this.copyElementCSSSelector(targetElement);
                break;
            case 'copyElementId':
                this.copyElementId(targetElement);
                break;
            case 'copyElementClass':
                this.copyElementClass(targetElement);
                break;
            case 'copyElementHTML':
                this.copyElementHTML(targetElement);
                break;
            case 'copyElementText':
                this.copyElementText(targetElement);
                break;
            
            // 요소 복사 관련
            case 'copyElementOnly':
                this.copyElementOnly(targetElement);
                break;
            case 'copyElementWithChildren':
                this.copyElementWithChildren(targetElement);
                break;
            
            // 수집 관련
            case 'collectById':
                this.collectById(targetElement);
                break;
            case 'collectByClass':
                this.collectByClass(targetElement);
                break;
            case 'collectByXPath':
                this.collectByXPath(targetElement);
                break;
            
            // 기타
            case 'inspectElement':
                this.inspectElement(targetElement);
                break;
        }
    }
    
    // XPath 복사
    copyElementXPath(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            const xpath = this.getElementXPath(targetElement);
            navigator.clipboard.writeText(xpath).then(() => {
                console.log('XPath 복사됨:', xpath);
                this.updateStatus('ready', 'XPath가 클립보드에 복사되었습니다');
            }).catch(err => {
                console.error('XPath 복사 실패:', err);
                this.updateStatus('error', 'XPath 복사 실패');
            });
        } catch (error) {
            console.error('XPath 생성 실패:', error);
            this.updateStatus('error', 'XPath 생성 실패');
        }
    }
    
    // CSS 선택자 복사
    copyElementCSSSelector(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            const selector = this.getElementCSSSelector(targetElement);
            navigator.clipboard.writeText(selector).then(() => {
                console.log('CSS 선택자 복사됨:', selector);
                this.updateStatus('ready', 'CSS 선택자가 클립보드에 복사되었습니다');
            }).catch(err => {
                console.error('CSS 선택자 복사 실패:', err);
                this.updateStatus('error', 'CSS 선택자 복사 실패');
            });
        } catch (error) {
            console.error('CSS 선택자 생성 실패:', error);
            this.updateStatus('error', 'CSS 선택자 생성 실패');
        }
    }
    
    // HTML 복사
    copyElementHTML(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            const html = targetElement.outerHTML;
            navigator.clipboard.writeText(html).then(() => {
                console.log('HTML 복사됨');
                this.updateStatus('ready', 'HTML이 클립보드에 복사되었습니다');
            }).catch(err => {
                console.error('HTML 복사 실패:', err);
                this.updateStatus('error', 'HTML 복사 실패');
            });
        } catch (error) {
            console.error('HTML 복사 실패:', error);
            this.updateStatus('error', 'HTML 복사 실패');
        }
    }
    
    // 텍스트 복사
    copyElementText(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            const text = targetElement.textContent || targetElement.innerText || '';
            navigator.clipboard.writeText(text).then(() => {
                console.log('텍스트 복사됨');
                this.updateStatus('ready', '텍스트가 클립보드에 복사되었습니다');
            }).catch(err => {
                console.error('텍스트 복사 실패:', err);
                this.updateStatus('error', '텍스트 복사 실패');
            });
        } catch (error) {
            console.error('텍스트 복사 실패:', error);
            this.updateStatus('error', '텍스트 복사 실패');
        }
    }
    
    // 요소 검사
    inspectElement(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            const elementInfo = this.getElementInfo(targetElement);
            console.log('요소 정보:', elementInfo);
            this.updateStatus('ready', '요소 검사 완료');
        } catch (error) {
            console.error('요소 검사 실패:', error);
            this.updateStatus('error', '요소 검사 실패');
        }
    }
    
    // XPath 생성
    getElementXPath(element) {
        if (element.id) {
            return `//*[@id="${element.id}"]`;
        }
        
        if (element === element.ownerDocument.body) {
            return '/html/body';
        }
        
        let ix = 0;
        const siblings = element.parentNode.childNodes;
        
        for (let i = 0; i < siblings.length; i++) {
            const sibling = siblings[i];
            if (sibling === element) {
                return this.getElementXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
            }
            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                ix++;
            }
        }
    }
    
    // Full XPath 생성 (절대 경로)
    getElementFullXPath(element) {
        if (element === element.ownerDocument.body) {
            return '/html/body';
        }
        
        if (element === element.ownerDocument.documentElement) {
            return '/html';
        }
        
        let ix = 0;
        const siblings = element.parentNode.childNodes;
        
        for (let i = 0; i < siblings.length; i++) {
            const sibling = siblings[i];
            if (sibling === element) {
                return this.getElementFullXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
            }
            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                ix++;
            }
        }
    }
    
    // CSS 선택자 생성
    getElementCSSSelector(element) {
        if (element.id) {
            return `#${element.id}`;
        }
        
        if (element.className) {
            const classes = element.className.split(' ').filter(c => c.trim());
            if (classes.length > 0) {
                return `${element.tagName.toLowerCase()}.${classes.join('.')}`;
            }
        }
        
        return element.tagName.toLowerCase();
    }
    
    // ID 복사
    copyElementId(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        const id = targetElement.id;
        if (!id) {
            this.updateStatus('error', '이 요소에는 ID가 없습니다');
            return;
        }
        
        navigator.clipboard.writeText(id).then(() => {
            console.log('ID 복사됨:', id);
            this.updateStatus('ready', 'ID가 클립보드에 복사되었습니다');
        }).catch(err => {
            console.error('ID 복사 실패:', err);
            this.updateStatus('error', 'ID 복사 실패');
        });
    }
    
    // 클래스 복사
    copyElementClass(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        const className = targetElement.className;
        if (!className) {
            this.updateStatus('error', '이 요소에는 클래스가 없습니다');
            return;
        }
        
        navigator.clipboard.writeText(className).then(() => {
            console.log('클래스 복사됨:', className);
            this.updateStatus('ready', '클래스가 클립보드에 복사되었습니다');
        }).catch(err => {
            console.error('클래스 복사 실패:', err);
            this.updateStatus('error', '클래스 복사 실패');
        });
    }
    
    // 해당 요소만 복사 (자식 제외)
    copyElementOnly(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            // 요소의 시작 태그만 복사 (자식 제외)
            const tagName = targetElement.tagName.toLowerCase();
            const id = targetElement.id ? ` id="${targetElement.id}"` : '';
            const className = targetElement.className ? ` class="${targetElement.className}"` : '';
            
            const elementOnly = `<${tagName}${id}${className}></${tagName}>`;
            
            navigator.clipboard.writeText(elementOnly).then(() => {
                console.log('요소만 복사됨:', elementOnly);
                this.updateStatus('ready', '요소만 클립보드에 복사되었습니다');
            }).catch(err => {
                console.error('요소 복사 실패:', err);
                this.updateStatus('error', '요소 복사 실패');
            });
        } catch (error) {
            console.error('요소 복사 실패:', error);
            this.updateStatus('error', '요소 복사 실패');
        }
    }
    
    // 자식 모두 복사
    copyElementWithChildren(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            return;
        }
        
        try {
            const html = targetElement.outerHTML;
            navigator.clipboard.writeText(html).then(() => {
                console.log('요소와 자식 모두 복사됨');
                this.updateStatus('ready', '요소와 자식 모두 클립보드에 복사되었습니다');
            }).catch(err => {
                console.error('요소와 자식 복사 실패:', err);
                this.updateStatus('error', '요소와 자식 복사 실패');
            });
        } catch (error) {
            console.error('요소와 자식 복사 실패:', error);
            this.updateStatus('error', '요소와 자식 복사 실패');
        }
    }
    
    // ID로 수집
    collectById(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            console.log('수집할 요소가 없습니다');
            return;
        }
        
        const id = targetElement.id;
        if (!id) {
            this.updateStatus('error', '이 요소에는 ID가 없습니다');
            return;
        }
        
        // 수집 셀에 ID 기반 수집 코드 추가
        const collectCode = `# ID로 수집: ${id}
elements = driver.find_elements(By.ID, "${id}")
for element in elements:
    print(element.text)`;
        
        this.addToCollectionCell(collectCode, `ID: ${id}`);
    }
    
    // 클래스로 수집
    collectByClass(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            console.log('수집할 요소가 없습니다');
            return;
        }
        
        const className = targetElement.className;
        if (!className) {
            this.updateStatus('error', '이 요소에는 클래스가 없습니다');
            return;
        }
        
        // 수집 셀에 클래스 기반 수집 코드 추가
        const collectCode = `# 클래스로 수집: ${className}
elements = driver.find_elements(By.CLASS_NAME, "${className}")
for element in elements:
    print(element.text)`;
        
        this.addToCollectionCell(collectCode, `클래스: ${className}`);
    }
    
    // XPath로 수집
    collectByXPath(element = null) {
        const targetElement = element || this.currentHoveredElement;
        if (!targetElement) {
            console.log('수집할 요소가 없습니다');
            return;
        }
        
        try {
            const xpath = this.getElementXPath(targetElement);
            
            // 수집 셀에 XPath 기반 수집 코드 추가
            const collectCode = `# XPath로 수집
elements = driver.find_elements(By.XPATH, "${xpath}")
for element in elements:
    print(element.text)`;
            
            this.addToCollectionCell(collectCode, `XPath: ${xpath}`);
        } catch (error) {
            console.error('XPath 생성 실패:', error);
            this.updateStatus('error', 'XPath 생성 실패');
        }
    }
    
    // 수집 셀에 코드 추가 (나중에 실제 구현)
    addToCollectionCell(code, description) {
        console.log('수집 셀에 추가:', description);
        console.log('코드:', code);
        
        // 현재는 콘솔에 출력하고 상태 업데이트
        this.updateStatus('ready', `수집 코드가 준비되었습니다: ${description}`);
        
        // TODO: 실제 수집 셀에 코드를 추가하는 로직 구현
        // 예: 노트북 셀에 코드 삽입, API 호출 등
    }
    
    // iframe으로부터 받은 메뉴 메시지 처리
    handleIframeMenuMessage(data) {
        console.log('iframe 메뉴 메시지 처리:', data);
        
        // 요소 정보로부터 가상의 요소 객체 생성
        const virtualElement = {
            tagName: data.elementTag || 'UNKNOWN',
            id: data.elementId || '',
            className: data.elementClass || '',
            textContent: data.elementText || '',
            outerHTML: `<${data.elementTag}${data.elementId ? ` id="${data.elementId}"` : ''}${data.elementClass ? ` class="${data.elementClass}"` : ''}>${data.elementText || ''}</${data.elementTag}>`
        };
        
        // 현재 선택된 요소로 설정
        this.currentHoveredElement = virtualElement;
        
        // 액션 처리
        this.handleIframeMenuAction(data.action, virtualElement);
    }
    
    // 우클릭 메뉴 숨기기 (기존 메서드 유지 - 호환성)
    hideContextMenu() {
        this.hideIframeContextMenu();
    }
    
    // 하이라이트 모드 전환
    toggleHighlightMode(mode) {
        this.highlightMode = mode;
        
        // 버튼 상태 업데이트
        document.querySelectorAll('.html-preview-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // iframe이 로드된 상태라면 이벤트 리스너 재설정
        if (this.isInitialized) {
            this.setupElementHighlighting();
        }
        
        this.updateStatus('ready', `${mode === 'hover' ? '호버' : '클릭'} 모드로 변경됨`);
    }
    
    // 상태 업데이트
    updateStatus(type, message) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        indicator.className = `status-indicator ${type}`;
        statusText.textContent = message;
    }

    // 현재 커널의 shared_dict에서 HTML 가져와서 뷰어에 표시
    async loadHTMLFromSharedDict(key = null) {
        if (!this.currentKernelId) {
            alert('커널이 없습니다. 먼저 커널을 생성해주세요.');
            return false;
        }
        
        try {
            const sharedDict = await this.getSharedDict();
            
            console.log('shared_dict 키들:', sharedDict ? Object.keys(sharedDict) : 'null');
            
            let htmlContent = null;
            let sourceType = null;
            let sourceData = null;
            
            // 1. 입력된 키가 있는지 확인
            if (key && key.trim() !== '') {
                if (sharedDict && sharedDict[key]) {
                    sourceData = sharedDict[key];
                    sourceType = key;
                }
            } else {
                // 2. 키가 없으면 SYSTEM_REQUEST, SYSTEM_SELENIUM 순서로 확인
                if (sharedDict && sharedDict['SYSTEM_REQUEST']) {
                    sourceData = sharedDict['SYSTEM_REQUEST'];
                    sourceType = 'SYSTEM_REQUEST';
                } else if (sharedDict && sharedDict['SYSTEM_SELENIUM']) {
                    sourceData = sharedDict['SYSTEM_SELENIUM'];
                    sourceType = 'SYSTEM_SELENIUM';
                }
            }
            
            // 3. 데이터 형식 확인 및 HTML 추출
            let cssList = []; // CSS 리스트 초기화
            
            if (sourceData) {
                console.log('데이터 형식 확인:', typeof sourceData, sourceType);
                
                // 4. dict형이면 class_job에서 리턴한 형태 (html 속성 사용)
                if (typeof sourceData === 'object' && sourceData !== null) {
                    if (sourceData.html) {
                        htmlContent = sourceData.html;
                        console.log('객체에서 html 속성 추출됨');
                    }
                    
                    // CSS 정보도 함께 가져오기 (css 또는 css_list 키 확인)
                    if (sourceData.css || sourceData.css_list) {
                        const cssListData = sourceData.css || sourceData.css_list;
                        
                        if (Array.isArray(cssListData)) {
                            cssList = cssListData;
                        } else if (typeof cssListData === 'string') {
                            console.log('CSS JSON 문자열 파싱 시도...');
                            try {
                                cssList = JSON.parse(cssListData);
                                console.log(`CSS 파싱 성공: ${cssList.length}개`);
                            } catch (e) {
                                console.warn('CSS JSON 파싱 실패:', e.message);
                                console.warn('데이터 미리보기:', cssListData.substring(0, 100));
                                cssList = [];
                            }
                        }
                    }
                }
                // 5. string형이면 그냥 HTML 코드
                else if (typeof sourceData === 'string') {
                    htmlContent = sourceData;
                    console.log('문자열 HTML 데이터 사용');
                }
            }
            
            if (htmlContent) {
                console.log(`HTML 데이터 로드: ${sourceType} (길이: ${htmlContent.length})`);
                console.log(`CSS 데이터: ${cssList.length}개`);
                
                // 디버깅: data URI 이미지 개수 확인
                const dataUriImgCount = (htmlContent.match(/src="data:image/g) || []).length;
                const dataBgCount = (htmlContent.match(/data-bg="data:image/g) || []).length;
                const cssBgCount = (htmlContent.match(/background-image:\s*url\("data:image/g) || []).length;
                console.log(`이미지 개수: img src=${dataUriImgCount}, data-bg=${dataBgCount}, css bg=${cssBgCount}`);
                
                // 디버깅: 실제 HTML 내용 일부 확인 (이미지 관련)
                const imgTags = htmlContent.match(/<img[^>]*>/g) || [];
                console.log(`=== IMG 태그 샘플 (처음 3개) ===`);
                imgTags.slice(0, 3).forEach((tag, i) => {
                    console.log(`IMG ${i+1}: ${tag}`);
                });
                
                // 원본 이미지 경로가 남아있는지 확인
                const originalImgCount = (htmlContent.match(/src="img\//g) || []).length;
                const originalBgCount = (htmlContent.match(/url\(['"]?img\//g) || []).length;
                console.log(`원본 경로 남은 개수: img src=${originalImgCount}, css bg=${originalBgCount}`);
                
                this.setHTML(htmlContent, cssList);
                this.updateStatus('ready', `${sourceType}에서 HTML 로드 완료`);
                return true;
            } else {
                const searchKey = key && key.trim() !== '' ? key : 'SYSTEM_REQUEST 또는 SYSTEM_SELENIUM';
                this.updateStatus('error', `${searchKey}에 HTML 데이터가 없습니다`);
                return false;
            }
        } catch (error) {
            console.error('HTML 로드 실패:', error.message);
            this.updateStatus('error', 'HTML 로드 실패: ' + error.message);
            return false;
        }
    }

    // ===== 자동 새로고침 관련 메서드들 =====
    
    /**
     * 자동 새로고침 토글
     */
    toggleAutoRefresh() {
        this.autoRefreshEnabled = !this.autoRefreshEnabled;
        const toggleBtn = document.getElementById('autoRefreshToggle');
        const icon = document.getElementById('autoRefreshIcon');
        
        if (this.autoRefreshEnabled) {
            this.startAutoRefresh();
            toggleBtn.classList.add('active');
            icon.textContent = '▶️';
            toggleBtn.title = '자동 새로고침 중지';
        } else {
            this.stopAutoRefresh();
            toggleBtn.classList.remove('active');
            icon.textContent = '⏸️';
            toggleBtn.title = '자동 새로고침 시작';
        }
        
        console.log('자동 새로고침:', this.autoRefreshEnabled ? '시작' : '중지');
    }
    
    /**
     * 자동 새로고침 시작 (타이머 기반 수동 새로고침)
     */
    startAutoRefresh() {
        this.stopAutoRefresh(); // 기존 타이머 정리
        
        const interval = this.getRefreshInterval();
        if (interval < 0.5) {
            console.warn('새로고침 간격이 너무 짧습니다. 0.5초로 설정합니다.');
            this.setRefreshInterval(0.5);
            return this.startAutoRefresh();
        }
        
        this.autoRefreshTimer = setInterval(() => {
            if (this.currentKernelId) {
                console.log(`타이머 기반 수동 새로고침 실행 (${interval}초 간격)`);
                this.refreshView(); // refreshSeleniumData 대신 refreshView 사용
            }
        }, interval * 1000);
        
        console.log(`타이머 기반 수동 새로고침 시작됨 (${interval}초 간격)`);
    }
    
    /**
     * 자동 새로고침 중지
     */
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
        }
    }
    
    /**
     * 새로고침 간격 가져오기 (검증 포함)
     */
    getRefreshInterval() {
        const input = document.getElementById('refreshInterval');
        let value = parseInt(input.value);
        
        // 숫자가 아니면 강제로 0.5초
        if (isNaN(value) || value < 0.5) {
            value = 0.5;
            input.value = value;
        }
        
        return value;
    }
    
    /**
     * 새로고침 간격 설정
     */
    setRefreshInterval(seconds) {
        const input = document.getElementById('refreshInterval');
        if (seconds < 0.5) seconds = 0.5;
        input.value = seconds;
        
        // 자동 새로고침이 활성화되어 있으면 재시작
        if (this.autoRefreshEnabled) {
            this.startAutoRefresh();
        }
    }
    
    // ===== 스크롤 동기화 관련 메서드들 =====
    

    
    /**
     * iframe과 selenium 간 스크롤 동기화 설정
     */
    setupScrollSync() {
        // 제거됨 - refresh API에서만 스크롤 동기화
        console.log('📍 스크롤 이벤트 제거됨 - refresh 시에만 동기화');
    }
    
    /**
     * 스크롤 동기화 해제
     */
    removeScrollSync() {
        // 제거됨 - 더 이상 스크롤 이벤트 없음
    }
    
    /**
     * iframe 스크롤 위치를 selenium으로 전송
     */
    syncScrollToSelenium(scrollX, scrollY) {
        // 제거됨 - refresh API에서 처리
    }
    
    // ===== 스크롤 위치 관리 =====
    
    /**
     * 현재 스크롤 위치 저장
     */
    saveScrollPosition() {
        try {
            const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
            if (iframeDoc) {
                this.lastScrollPosition = {
                    x: iframeDoc.documentElement.scrollLeft || iframeDoc.body.scrollLeft || 0,
                    y: iframeDoc.documentElement.scrollTop || iframeDoc.body.scrollTop || 0
                };
                console.log('스크롤 위치 저장됨:', this.lastScrollPosition);
            }
        } catch (e) {
            // sandbox 제한으로 인한 정상적인 오류
            console.log('스크롤 위치 저장 불가:', e.message);
        }
    }
    
    /**
     * 저장된 스크롤 위치로 복원
     */
    restoreScrollPosition() {
        if (this.lastScrollPosition.x === 0 && this.lastScrollPosition.y === 0) {
            return; // 초기 상태이므로 복원할 필요 없음
        }
        
        // 약간의 지연 후 스크롤 복원 (iframe 완전 로드 대기)
        setTimeout(() => {
            try {
                const iframeDoc = this.iframe.contentDocument || this.iframe.contentWindow.document;
                if (iframeDoc) {
                    iframeDoc.documentElement.scrollTo(this.lastScrollPosition.x, this.lastScrollPosition.y);
                    console.log('스크롤 위치 복원됨:', this.lastScrollPosition);
                }
            } catch (e) {
                // sandbox 제한으로 인한 정상적인 오류
                console.log('스크롤 위치 복원 불가:', e.message);
            }
        }, 100);
    }
    
    // ===== 유틸리티 메서드들 =====
    
    /**
     * 컴포넌트 정리 (페이지 언로드 시)
     */
    cleanup() {
        this.stopAutoRefresh();
        // removeScrollSync() 제거됨 - 스크롤 이벤트 없음
        
        console.log('HTML 뷰어 정리 완료');
    }

    /**
     * 디바운싱 함수 (과도한 이벤트 호출 방지)
     */
    debounce(func, wait) {
        // 제거됨 - 스크롤 이벤트 없어서 더 이상 필요없음
    }

    // ===== 컴포넌트 정리 =====

    // ===== 디버깅 메서드들 =====
    
    /**
     * 스크롤 동기화 테스트
     */
    testScrollSync(x = 100, y = 100) {
        console.log(`🧪 스크롤 동기화 테스트: (${x}, ${y})`);
        this.lastScrollPosition = { x, y };
        this.refreshSeleniumData();
    }
    
    // ===== 유틸리티 메서드들 =====
}

// HTML 뷰어 인스턴스 즉시 생성
const htmlViewerInstance = new HTMLViewer();

// 전역 함수들 (HTML에서 직접 호출)
async function refreshView() {
    await htmlViewerInstance.refreshView();
}

async function forceRefreshView() {
    await htmlViewerInstance.forceRefreshView();
}

function clearView() {
    htmlViewerInstance.clearView();
}

function toggleHighlightMode(mode) {
    htmlViewerInstance.toggleHighlightMode(mode);
}

// 외부에서 HTML 설정하는 함수
function setHTMLContent(htmlContent, cssList = []) {
    htmlViewerInstance.setHTML(htmlContent, cssList);
}

// 커널 ID 설정 함수 (외부에서 호출)
function setKernelId(kernelId) {
    htmlViewerInstance.setKernelId(kernelId);
}

// 커널 ID 가져오기 함수 (외부에서 호출)
function getKernelId() {
    return htmlViewerInstance.getKernelId();
}

// shared_dict에서 HTML 로드하는 전역 함수
async function loadHTMLFromSharedDict(key = null) {
    // key가 null이면 입력 필드에서 값을 가져옴
    if (key === null) {
        const keyInput = document.getElementById('keyInput');
        if (keyInput) {
            key = keyInput.value.trim();
        }
    }
    
    // 키가 비어있으면 null로 전달하여 기본값(SYSTEM_REQUEST) 사용
    if (key === '') {
        key = null;
    }
    
    return await htmlViewerInstance.loadHTMLFromSharedDict(key);
}

// 우클릭 메뉴 함수들 (iframe 내부 메뉴로 대체됨)
function copyXPath() {
    htmlViewerInstance.copyElementXPath();
}

function copyCSSSelector() {
    htmlViewerInstance.copyElementCSSSelector();
}

function copyElementId() {
    htmlViewerInstance.copyElementId();
}

function copyElementClass() {
    htmlViewerInstance.copyElementClass();
}

function copyElementHTML() {
    htmlViewerInstance.copyElementHTML();
}

function copyElementText() {
    htmlViewerInstance.copyElementText();
}

function copyElementOnly() {
    htmlViewerInstance.copyElementOnly();
}

function copyElementWithChildren() {
    htmlViewerInstance.copyElementWithChildren();
}

function collectById() {
    htmlViewerInstance.collectById();
}

function collectByClass() {
    htmlViewerInstance.collectByClass();
}

function collectByXPath() {
    htmlViewerInstance.collectByXPath();
}

function inspectElement() {
    htmlViewerInstance.inspectElement();
}

// 자동 새로고침 토글 (HTML에서 직접 호출)
function toggleAutoRefresh() {
    htmlViewerInstance.toggleAutoRefresh();
}



// 창 크기 변경 시 하이라이트 위치 재조정
window.addEventListener('resize', function() {
    if (htmlViewerInstance && htmlViewerInstance.currentHighlight) {
        // 현재 하이라이트된 요소가 있다면 위치 재조정
        const iframeDoc = htmlViewerInstance.iframe.contentDocument || htmlViewerInstance.iframe.contentWindow.document;
        const activeElement = iframeDoc.querySelector(':hover');
        if (activeElement) {
            htmlViewerInstance.highlightElement(activeElement, {});
        }
    }
});

// 새로고침 간격 input 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
    // 페이지 언로드 시 정리
    window.addEventListener('beforeunload', function() {
        if (htmlViewerInstance) {
            htmlViewerInstance.cleanup();
        }
    });
    
    // 새로고침 간격 input 값 변경 이벤트
    setTimeout(() => {
        const refreshInput = document.getElementById('refreshInterval');
        if (refreshInput) {
            refreshInput.addEventListener('change', function() {
                const value = parseInt(this.value);
                if (isNaN(value) || value < 3) {
                    this.value = 5;
                    console.warn('새로고침 간격은 최소 3초입니다. 5초로 설정했습니다.');
                }
                
                // 자동 새로고침이 활성화되어 있으면 재시작
                if (htmlViewerInstance && htmlViewerInstance.autoRefreshEnabled) {
                    htmlViewerInstance.startAutoRefresh();
                    console.log(`새로고침 간격 변경: ${this.value}초`);
                }
            });
            
            refreshInput.addEventListener('input', function() {
                // 실시간으로 값 검증
                let value = parseInt(this.value);
                if (value < 3 && this.value !== '') {
                    this.value = 3;
                }
            });
        }
    }, 100); // HTML이 완전히 로드된 후 실행
}); 

// 커널 shared_dict 테스트 함수 (새로 추가)
async function testSharedDict() {
    if (!htmlViewerInstance.currentKernelId) {
        htmlViewerInstance.updateStatus('error', '커널 ID가 설정되지 않았습니다');
        return;
    }
    
    try {
        // 1. 커널 shared_dict 가져오기
        const sharedDict = await htmlViewerInstance.getSharedDict();
        
        if (sharedDict) {
            console.log('shared_dict 키들:', Object.keys(sharedDict));
            htmlViewerInstance.updateStatus('ready', `커널 shared_dict 테스트 완료 - 키 ${Object.keys(sharedDict).length}개`);
        } else {
            htmlViewerInstance.updateStatus('error', '커널 shared_dict를 가져올 수 없습니다');
        }
    } catch (error) {
        console.error('shared_dict 테스트 중 오류:', error);
        htmlViewerInstance.updateStatus('error', '테스트 중 오류: ' + error.message);
    }
} 

// 스크롤 동기화 테스트 함수 (브라우저 콘솔에서 사용)
function testScrollSync(x = 100, y = 100) {
    if (htmlViewerInstance) {
        htmlViewerInstance.testScrollSync(x, y);
    } else {
        console.error('HTML 뷰어 인스턴스가 없습니다');
    }
}

// 수동 새로고침 테스트 함수
function testRefreshView() {
    if (htmlViewerInstance) {
        htmlViewerInstance.refreshView();
    } else {
        console.error('HTML 뷰어 인스턴스가 없습니다');
    }
}