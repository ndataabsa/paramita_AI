#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# CLASS 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'CLASS'))

from CLASS import class_job
from CLASS import DATA_Result

def test_job():
    """test 타입 job을 테스트하는 함수"""
    
    # 테스트할 job 데이터
    test_jobs = [
        {
            "name": "테스트 변수 저장",
            "type": "test",
            "params": {
                "test_type": "variable",
                "name": "test_var",
                "value": "안녕하세요! 테스트입니다.",
                "print_result": True
            }
        },
        {
            "name": "테스트 리스트 생성",
            "type": "test",
            "params": {
                "test_type": "list",
                "name": "test_list",
                "items": "사과,바나나,오렌지,포도",
                "print_result": True
            }
        },
        {
            "name": "테스트 딕셔너리 생성",
            "type": "test",
            "params": {
                "test_type": "dict",
                "name": "test_dict",
                "key_value_pairs": "이름:홍길동,나이:30,도시:서울,직업:개발자",
                "print_result": True
            }
        }
    ]
    
    # 공유 데이터 딕셔너리 (테스트용 mock engine 포함)
    class MockEngine:
        def __init__(self):
            pass
    
    data_share_dict = {
        'worker_class_engine': MockEngine()
    }
    
    print("=== test 타입 job 테스트 시작 ===\n")
    
    for i, job_data in enumerate(test_jobs, 1):
        print(f"--- Job {i}: {job_data['name']} ---")
        
        # Job 인스턴스 생성
        job = Job(job_data['name'], job_data['params'], data_share_dict)
        
        # job 실행
        result = job.run()
        
        # 결과 출력
        if result['result']:
            print(f"✅ 성공: {result['message']}")
        else:
            print(f"❌ 실패: {result['message']}")
        
        print()
    
    print("=== 저장된 변수들 ===")
    for key, value in data_share_dict.items():
        print(f"{key}: {value}")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_job() 