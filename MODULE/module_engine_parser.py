import sys
import os
import re
import json
from CLASS import class_parser_html

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# high level parse language

class parser:
    def __init__(self,driver):
        self.driver = driver
        self.root = self.parse(self.driver.page_source)

    def parse(self, html_content):
        """HTML 내용을 파싱합니다."""
        return class_parser_html.parse(html_content)

    def refresh(self): 
        self.root = self.parse(self.driver.page_source)

    