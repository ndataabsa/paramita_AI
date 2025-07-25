#!/usr/bin/env python3
import time
import psutil
import sys
import signal
from datetime import datetime

def monitor_chrome_process(pid, timeout_minutes=1440):
    """특정 크롬 프로세스 모니터링"""
    start_time = datetime.now()
    
    def signal_handler(signum, frame):
        """시그널 핸들러"""
        print("모니터링 종료")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f'타이머: PID {pid} 모니터링 시작 (타임아웃: {timeout_minutes}분)')
    
    while True:
        try:
            process = psutil.Process(pid)
            if not process.is_running():
                print(f'타이머: PID {pid} 프로세스 종료됨')
                sys.exit(0)
                
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
            if elapsed_minutes >= timeout_minutes:
                process.terminate()
                print(f'타이머: PID {pid} 타임아웃으로 종료')
                sys.exit(0)
                
        except psutil.NoSuchProcess:
            print(f'타이머: PID {pid} 프로세스 종료됨')
            sys.exit(0)
            
        time.sleep(60)  # 1분마다 체크

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("사용법: python module_engine_timer.py <pid> <timeout_minutes>")
        sys.exit(1)
        
    try:
        pid = int(sys.argv[1])
        timeout = int(sys.argv[2])
        monitor_chrome_process(pid, timeout)
    except ValueError:
        print("PID와 타임아웃은 정수여야 합니다.")
        sys.exit(1) 