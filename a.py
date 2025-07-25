# -*- coding: utf-8 -*-
# NP Notebook에서 변환된 Python 코드

# 경로 설정 및 class_job import
import os
import sys
current_dir = os.getcwd()
if os.path.exists(os.path.join(current_dir, 'CLASS')):
    sys.path.append(os.path.join(current_dir, 'CLASS'))
    sys.path.append(os.path.join(current_dir, 'MODULE'))
elif os.path.exists(os.path.join(current_dir, '..', 'CLASS')):
    sys.path.append(os.path.join(current_dir, '..', 'CLASS'))
    sys.path.append(os.path.join(current_dir, '..', 'MODULE'))
else:
    print("CLASS/MODULE 폴더를 찾을 수 없습니다. 경로를 확인해주세요.")
    print(f"현재 디렉토리: {current_dir}")
from class_job import Job

# shared_dict 초기화
if 'shared_dict' not in globals():
    globals()['shared_dict'] = {}
    print("공용 데이터 딕셔너리 초기화됨")
shared_dict = globals()['shared_dict']

# 셀 1
print("=== 셀 1 실행 ===\n")


# 셀 2
print("=== 셀 2 실행 ===\n")

# job_2 - request get
job_name = "job_2"
job_args = {
    "type": "request",
    "url": "https://n-data.co.kr",
    "request_type": "get"
}

# Job 객체 생성 및 실행
try:
    job = Job(job_name, job_args, shared_dict)
    result = job.run()
    print(f"Job '{job_name}' 실행 결과: {result}")
    # job 결과를 shared_dict에 job name을 키로 저장
    shared_dict[job_name] = result
    print(f"Job 결과가 shared_dict['{job_name}']에 저장되었습니다.")
    if hasattr(result, 'data') and result.data is not None:
        print(f"결과 데이터: {result.data}")
    if hasattr(result, 'message') and result.message:
        print(f"메시지: {result.message}")
except Exception as e:
    print(f"Job 실행 중 오류 발생: {str(e)}")
    import traceback
    traceback.print_exc()

print("Job 실행 완료")

# 셀 3
print("=== 셀 3 실행 ===\n")

print(shared_dict['SYSTEM_REQUEST']['html'][:20])

# 셀 4
print("=== 셀 4 실행 ===\n")

print("XXX")

