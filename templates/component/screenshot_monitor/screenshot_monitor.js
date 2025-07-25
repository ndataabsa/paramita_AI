/**
 * 실시간 스크린샷 모니터링 시스템
 * 커널 상태를 감지하고 SYSTEM_SELENIUM이 활성화되면 실시간 스크린샷을 제공
 */

class ScreenshotMonitor {
    constructor() {
        this.isActive = false;
        this.currentKernelId = null;
        this.screenshotInterval = null;
        this.lastScreenshotTime = null;
        this.tempFolder = null;
        
        this.init();
    }

    init() {

        this.updateUI();
        // this.startMonitoring(); // 스크린샷 자동 모니터링 일시 중단
    }

    // 커널 상태 모니터링 시작
    // startMonitoring() {
    //     // 2초마다 커널 상태 확인
    //     setInterval(() => {
    //         this.checkKernelStatus();
    //     }, 2000);
    // }

    // 커널 상태 확인
    async checkKernelStatus() {
        try {
            const response = await fetch('/api/session/kernel/status');
            const data = await response.json();
            
            if (data.success && data.kernel_id) {
                const kernelId = data.kernel_id;
                
                // 커널이 변경되었거나 새로 생성된 경우
                if (this.currentKernelId !== kernelId) {
        
                    this.currentKernelId = kernelId;
                    this.onKernelChanged(kernelId);
                }
            } else {
                // 커널이 비활성화된 경우
                if (this.currentKernelId !== null) {
    
                    this.currentKernelId = null;
                    this.stopScreenshotCapture();
                }
            }
        } catch (error) {
            console.error('📸 커널 상태 확인 오류:', error);
        }
    }

    // 커널 변경 시 처리
    async onKernelChanged(kernelId) {
        
        
        // SYSTEM_SELENIUM 상태 확인
        const hasSelenium = await this.checkSeleniumStatus(kernelId);
        
        if (hasSelenium) {
            
            this.startScreenshotCapture(kernelId);
        } else {

            this.stopScreenshotCapture();
        }
    }

    // SYSTEM_SELENIUM 상태 확인
    async checkSeleniumStatus(kernelId) {
        try {
            const response = await fetch(`/api/kernels/${kernelId}/namespace`);
            const data = await response.json();
            
            if (data.success && data.namespace) {
                // SYSTEM_SELENIUM이 namespace에 있는지 확인
                return 'SYSTEM_SELENIUM' in data.namespace && data.namespace.SYSTEM_SELENIUM !== null;
            }
        } catch (error) {
            console.error('📸 Selenium 상태 확인 오류:', error);
        }
        return false;
    }

    // 스크린샷 캡처 시작
    async startScreenshotCapture(kernelId) {
        // 스크린샷 자동 캡처 일시 중단

        return;
        if (this.isActive) {
            return; // 이미 활성화된 경우
        }

        try {
            // temp 폴더 생성 요청
            const response = await fetch('/api/screenshot/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ kernel_id: kernelId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isActive = true;
                this.tempFolder = data.temp_folder;
    
                
                // 1초마다 스크린샷 업데이트
                this.screenshotInterval = setInterval(() => {
                    this.updateScreenshot();
                }, 1000);
                
                this.updateUI();
            } else {
                console.error('📸 스크린샷 캡처 시작 실패:', data.message);
            }
        } catch (error) {
            console.error('📸 스크린샷 캡처 시작 오류:', error);
        }
    }

    // 스크린샷 캡처 중지
    stopScreenshotCapture() {
        if (!this.isActive) {
            return;
        }

        
        
        if (this.screenshotInterval) {
            clearInterval(this.screenshotInterval);
            this.screenshotInterval = null;
        }
        
        this.isActive = false;
        this.tempFolder = null;
        this.lastScreenshotTime = null;
        
        // UI 업데이트
        this.hideScreenshot();
        this.updateUI();
        
        // temp 폴더 정리 요청
        if (this.currentKernelId) {
            fetch('/api/screenshot/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ kernel_id: this.currentKernelId })
            }).catch(error => {
                console.error('📸 스크린샷 정리 오류:', error);
            });
        }
    }

    // 스크린샷 업데이트
    async updateScreenshot() {
        // 스크린샷 자동 갱신 일시 중단
        return;
        if (!this.isActive || !this.tempFolder) {
            return;
        }

        try {
            const response = await fetch(`/api/screenshot/latest?temp_folder=${encodeURIComponent(this.tempFolder)}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);
                
                this.displayScreenshot(imageUrl);
                this.lastScreenshotTime = new Date();
                this.updateUI();
            }
        } catch (error) {
            console.error('📸 스크린샷 업데이트 오류:', error);
        }
    }

    // 스크린샷 표시
    displayScreenshot(imageUrl) {
        const imageElement = document.getElementById('screenshot-image');
        const placeholderElement = document.getElementById('screenshot-placeholder');
        
        if (imageElement && placeholderElement) {
            imageElement.src = imageUrl;
            imageElement.style.display = 'block';
            placeholderElement.style.display = 'none';
        }
    }

    // 스크린샷 숨김
    hideScreenshot() {
        const imageElement = document.getElementById('screenshot-image');
        const placeholderElement = document.getElementById('screenshot-placeholder');
        
        if (imageElement && placeholderElement) {
            imageElement.style.display = 'none';
            placeholderElement.style.display = 'block';
        }
    }

    // UI 업데이트
    updateUI() {
        const kernelIdElement = document.getElementById('screenshot-kernel-id');
        const statusElement = document.getElementById('screenshot-status');
        const lastUpdateElement = document.getElementById('screenshot-last-update');
        const statusTextElement = document.getElementById('screenshot-status-text');
        
        if (kernelIdElement) {
            kernelIdElement.textContent = this.currentKernelId || '없음';
        }
        
        if (statusElement) {
            if (this.isActive) {
                statusElement.textContent = '활성';
                statusElement.style.color = '#48bb78';
            } else {
                statusElement.textContent = '비활성';
                statusElement.style.color = '#e53e3e';
            }
        }
        
        if (lastUpdateElement) {
            if (this.lastScreenshotTime) {
                lastUpdateElement.textContent = this.lastScreenshotTime.toLocaleTimeString();
            } else {
                lastUpdateElement.textContent = '-';
            }
        }
        
        if (statusTextElement) {
            if (this.isActive) {
                statusTextElement.textContent = '실시간 스크린샷이 캡처되고 있습니다.';
            } else {
                statusTextElement.textContent = '커널이 활성화되면 실시간 스크린샷이 표시됩니다.';
            }
        }
    }

    // 패널 토글
    togglePanel() {
        const panel = document.getElementById('screenshotPanel');
        if (panel) {
            panel.classList.toggle('open');
        }
    }
}

// 전역 변수로 인스턴스 생성
let screenshotMonitor = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    screenshotMonitor = new ScreenshotMonitor();
});

// 전역 함수들
function toggleScreenshotPanel() {
    if (screenshotMonitor) {
        screenshotMonitor.togglePanel();
    }
}

// 커널 상태 변경 시 호출되는 함수 (기존 코드에서 호출)
function onKernelStatusChanged() {
    if (screenshotMonitor) {
        // 커널 상태 변경을 감지하도록 강제로 상태 확인
        setTimeout(() => {
            screenshotMonitor.checkKernelStatus();
        }, 1000);
    }
} 