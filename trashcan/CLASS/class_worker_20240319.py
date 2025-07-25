import json
import sys
import os
import time
import random
import threading
import queue
import signal
import psutil
import subprocess

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MODULE.module_engine_selenium import engine
from CLASS.class_parser_html import parser
from class_job import Job

class Worker:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.jobs = []
        self.selenium_engine = engine()
        self.data_share_dict = {'worker_class_engine':self.selenium_engine} 
        
        # default
        self.default_sleep = 0.1
        self.default_interval = 0.1
        self.type = 'selenium'
        self.url = ''
        
        self.load_config()

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            work_data = self.config['worker']
            
            # 기본 설정값 가져오기
            self.default_sleep = work_data.get('default_sleep', 0.1)
            self.default_interval = work_data.get('default_interval', 0.1)
            self.type = work_data.get('type', 'selenium')
            self.url = work_data.get('url', '')
            
            # job 이름 중복 체크를 위한 딕셔너리
            job_names = {}
            
            # Job 객체 리스트 생성
            self.jobs = []
            for job in work_data['jobs']:
                original_name = job['name']
                
                # worker_class_ 체크
                if 'worker_class_' in original_name:
                    print(f"Error: Job name '{original_name}' cannot contain 'worker_class_'")
                    continue
                
                # 이름이 중복되면 숫자 붙이기
                if original_name in job_names:
                    job_names[original_name] += 1
                    job['name'] = f"{original_name}_{job_names[original_name]}"
                else:
                    job_names[original_name] = 0
                
                self.jobs.append(Job(
                    name=job['name'],
                    args=job['params'],
                    data_share_dict=self.data_share_dict
                ))

    def get_jobs(self):
        return self.jobs

    def get_config(self):
        return self.config 
    
    def run(self):
        for job in self.jobs:
            result = job.run()
            self.data_share_dict[job.name] = result
            time.sleep(self.default_sleep+random.uniform(0,self.default_interval))

    def get_results(self):
        return self.data_share_dict
