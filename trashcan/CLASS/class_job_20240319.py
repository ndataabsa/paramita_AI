import sys
import os
import traceback

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from CLASS.class_parser_html import parser

class Job:
    def __init__(self, name, args, data_share_dict):
        self.name = name
        self.args = args
        self.data_share_dict = data_share_dict
        self.engine = self.data_share_dict['worker_class_engine']
        self.driver_number = self.data_share_dict.get('driver_number', 0)
        # self.type = args.get('type', 'do')  # 기본값은 'do'
        # self.action = args.get('action', '')  # click, input 등의 액션
        # self.selector = args.get('selector', '')  # CSS 선택자
        # self.xpath = args.get('xpath', '')  # XPath
        # self.speed = args.get('speed', 0.1)  # 동작 속도

    def find_element(self):
        if self.args.get('focus'):
            if self.args['focus'].get('xpath'):
                return self.engine.find_element_xpath(self.args['focus']['xpath'])
            elif self.args['focus'].get('selector'):
                xpath = parser.to_xpath(self.args['focus']['selector'])
                return self.engine.find_element_xpath(xpath)
            elif self.args['focus'] == 'current':
                return self.engine.drivers[self.driver_number].switch_to.active_element
        return None

    def refresh(self):
        self.driver_number = self.data_share_dict.get('driver_number', 0)
        return True

    def do_scroll(self, element=None):
        sleep = float(self.args['sleep'])
        max_time = int(self.args['max_time'])
        speed_variation = float(self.args['speed_variation'])
        
        if self.args['type'] == 'scroll': return self.engine.scroll(self.driver_number, sleep, max_time)
        elif self.args['type'] == 'scroll_smooth': return self.engine.smooth_scroll(self.driver_number, sleep, max_time, speed_variation)
        elif self.args['type'] == 'scroll_to_element':
            if not element: return None
            xpath = element.to_xpath()
            
            if self.args['smooth']:
                scroll_speed = int(self.args['scroll_speed'])
                return self.engine.smooth_scroll_to_element(self.driver_number, xpath, sleep, scroll_speed, speed_variation, max_time)
            else: return self.engine.scroll_to_element(self.driver_number, xpath)
        return None

    def run(self):
        element = self.find_element()
        
        if self.args['type'] == 'do':
            if not element:
                return None
            xpath = element.to_xpath()
            if self.args['action'] == 'click':
                self.engine.do_click(self.driver_number, xpath)
                return True
            else:
                return element.text
        elif self.args['type'] in ['scroll', 'scroll_smooth', 'scroll_to_element']:
            return self.do_scroll(element)
        return None

